"""
执行器模块：负责读取规划器输出的 JSON，并按步骤调用技能完成任务。
核心要求：
1) 继续调用底层 AIAgent（已加载技能提示词），由模型参与参数填充与调用控制。
2) 严格按 excute plan 顺序执行，记录每个步骤的执行结果。
3) 处理多步骤依赖时的 JSON 信息流，利用前置步骤结果填充后置参数。
4) 提供终端测试入口：联动 AgentPlanner 生成规划并执行。
"""

import os
import sys
import json
from typing import Any, Dict, List

# 将项目根目录加入 sys.path，保证跨目录导入稳定
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from core.ai_agent import AIAgent
from core.core_agent.agent_planner import AgentPlanner
from ai_tools import skill_registry


class AgentExecutor:
    """
    执行器：执行规划器生成的任务计划，并写回每一步结果。
    """

    def __init__(self):
        """
        初始化执行器，加载底层 AIAgent。
        """
        self.agent = AIAgent()
        self.skills_metadata_path = os.path.join(project_root, "ai_tools", "skills_metadata.json")
        self.full_skills_map = self._load_full_skills_map()

    def execute_plan(self, plan_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行规划 JSON，并将每一步执行结果写回到 excute plan 中。
        """
        # 统一规划结构，避免字段缺失
        plan = self._normalize_plan(plan_json)
        plan_steps = plan.get("excute plan", [])
        if not isinstance(plan_steps, list) or not plan_steps:
            return plan

        context_memory = []
        for step in plan_steps:
            # 逐步执行，并将结果写回到计划中
            step_result = self._execute_single_step(step, context_memory)
            step["step results"] = step_result
            context_memory.append({
                "step": step.get("step"),
                "desc": step.get("desc"),
                "skill": step.get("skill", {}).get("name"),
                "result": step_result
            })

        return plan

    def excute_plan_stream(self, plan_json: Dict[str, Any]):
        """
        实时流式输出excute_plan的执行结果中的result字段的message字段信息，保证用户及时了解任务进度。
        """
        # 先做结构规范化，保证后续字段可用
        plan = self._normalize_plan(plan_json)
        plan_steps = plan.get("excute plan", [])
        if not isinstance(plan_steps, list) or not plan_steps:
            return plan

        context_memory = []
        for step in plan_steps:
            # 逐步执行，确保每一步完成后立即输出核心进度信息
            step_result = self._execute_single_step(step, context_memory)
            step["step results"] = step_result

            # 写入上下文，供后续步骤参数填充与依赖处理
            context_memory.append({
                "step": step.get("step"),
                "desc": step.get("desc"),
                "skill": step.get("skill", {}).get("name"),
                "result": step_result
            })

            # 真实流式输出当前步骤的核心字段内容
            step_no = step.get("step")
            message = step_result.get("message") if isinstance(step_result, dict) else None
            if not message:
                message = "执行完成"
            print(f"步骤{step_no}：调用技能{step.get('skill', {}).get('name')}", flush=True)
            print(f"步骤{step_no}：{message}", flush=True)

        return plan

    def _execute_single_step(self, step: Dict[str, Any], context_memory: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        执行单个步骤：优先让模型生成工具调用 JSON，再执行技能。
        """
        if not isinstance(step, dict):
            return {"success": False, "message": "步骤数据格式错误", "error": "step_not_dict"}

        skill_info = step.get("skill") if isinstance(step.get("skill"), dict) else {}
        skill_name = skill_info.get("name")
        skill_arguments = skill_info.get("arguments", {})

        if not skill_name:
            return {"success": False, "message": "缺少技能名称", "error": "missing_skill_name"}

        # 构建提示词，要求模型基于上下文填充参数并调用指定技能
        prompt = self._build_step_prompt(step, context_memory, skill_name, skill_arguments)
        llm_result = self.agent.call_core(
            prompt,
            stream=False,
            max_tool_steps=0,
            record_memory=False,
            use_memory=False
        )
        tool_calls = llm_result.get("tool_calls", []) if isinstance(llm_result, dict) else []

        if tool_calls:
            # 记录本轮执行已触发工具调用，供 UI 刷新使用
            self.agent.tool_executed_in_last_chat = True
            return self._build_step_result_from_tool_calls(tool_calls)

        # 模型未返回工具调用时，直接执行技能兜底
        # 模型未触发工具调用时，仍然执行兜底技能并标记为已执行
        fallback_result = self._execute_skill_fallback(skill_name, skill_arguments)
        self.agent.tool_executed_in_last_chat = True
        return self._build_step_result_from_fallback(fallback_result)

    def _build_step_prompt(self, step: Dict[str, Any], context_memory: List[Dict[str, Any]],
                           skill_name: str, skill_arguments: Any) -> str:
        """
        构造模型提示词，指导其从上下文中填充参数并调用指定技能。
        """
        # 增加上下文长度，确保文件列表等关键信息不被截断
        context_text = self._truncate_text(json.dumps(context_memory, ensure_ascii=False), 8000)
        skill_args_text = self._truncate_text(json.dumps(skill_arguments, ensure_ascii=False), 2000)
        skill_schema = self._get_skill_schema(skill_name)
        skill_schema_text = json.dumps(skill_schema, ensure_ascii=False) if skill_schema else ""

        return (
            "你是任务执行器，必须调用指定技能完成当前步骤。"
            "你的核心任务是：基于步骤描述与历史步骤结果，智能填充技能参数。"
            "特别注意：如果参数需要从历史结果中提取（例如文件名、路径、ID），请仔细查找并使用确切值，绝不要使用'从上一步获取'之类的描述性文字。"
            "如果用户需求模糊（如'那个pdf'），请从历史结果中找到最匹配的项。"
            "如果用户要求查询github仓库信息，或文件信息时，默认采用递归查询要尽量详尽，将所有相关信息都包含在查询结果中。"
            "\n\n[当前步骤]"
            f"\nstep: {step.get('step')}"
            f"\ndesc: {step.get('desc')}"
            f"\n指定技能: {skill_name}"
            f"\n原始参数: {skill_args_text}"
            f"\n\n[技能参数定义]\n{skill_schema_text}"
            f"\n\n[历史步骤结果]\n{context_text}\n"
            "\n输出要求："
            "1. 输出严格 JSON 格式：{\"action\": \"call_skill\", \"name\": \"技能名\", \"arguments\": {参数}}。"
            "2. 参数必须是真实值，不能是占位符。"
            "3. 不要输出多余文字。"
        )

    def _execute_skill_fallback(self, skill_name: str, skill_arguments: Any) -> Any:
        """
        当模型未返回工具调用时，直接执行技能作为兜底。
        """
        # 从技能注册表获取真实函数
        func = skill_registry.get_skill_function(skill_name)
        if not func:
            return {"status": "error", "message": f"未注册技能：{skill_name}"}
        try:
            normalized_arguments = skill_registry.normalize_skill_arguments(skill_name, skill_arguments)
            return func(**normalized_arguments) if isinstance(normalized_arguments, dict) else func(normalized_arguments)
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def _build_step_result_from_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        将模型执行的技能调用结果转换为统一的步骤结果结构。
        """
        # 聚合多个工具调用结果
        success = True
        messages = []
        for call in tool_calls:
            result = call.get("result")
            step_success, message = self._analyze_result(result)
            success = success and step_success
            messages.append(message)

        return {
            "success": success,
            "message": "；".join([m for m in messages if m]),
            "data": tool_calls
        }

    def _build_step_result_from_fallback(self, fallback_result: Any) -> Dict[str, Any]:
        """
        将兜底技能执行结果转换为统一步骤结果结构。
        """
        success, message = self._analyze_result(fallback_result)
        result = {
            "success": success,
            "message": message,
            "data": fallback_result
        }
        if not success and isinstance(fallback_result, dict) and fallback_result.get("message"):
            result["error"] = fallback_result.get("message")
        return result

    def _analyze_result(self, result: Any) -> tuple[bool, str]:
        """
        对不同类型的技能返回结果进行成功判定与摘要。
        """
        # 字典结果：优先读取 status / success / message
        if isinstance(result, dict):
            if result.get("status") == "error" or result.get("success") is False:
                return False, result.get("message", "执行失败")
            return True, result.get("message", "执行成功")

        # 列表结果：统计失败数量
        if isinstance(result, list):
            failures = [item for item in result if isinstance(item, dict) and item.get("success") is False]
            if failures:
                return False, f"❌失败 {len(failures)} 项"
            return True, f"✅成功 {len(result)} 项"

        return True, "执行完成"

    def _normalize_plan(self, plan_json: Any) -> Dict[str, Any]:
        """
        规范化输入的规划 JSON，保证关键字段存在。
        """
        if not isinstance(plan_json, dict):
            return {
                "is skills": False,
                "description": [],
                "excute plan": [],
                "thinking": str(plan_json or "")
            }

        # 为缺失字段补默认值，确保后续逻辑稳定
        plan_json.setdefault("is skills", False)
        plan_json.setdefault("description", [])
        plan_json.setdefault("excute plan", [])
        plan_json.setdefault("thinking", "")
        return plan_json

    def _truncate_text(self, text: str, max_len: int) -> str:
        """
        防止上下文过长导致模型输入异常。
        """
        if not isinstance(text, str):
            text = str(text)
        return text if len(text) <= max_len else text[:max_len] + "..."

    def _load_full_skills_map(self):
        data = self._read_json(self.skills_metadata_path)
        skills = data.get("skills", []) if isinstance(data, dict) else []
        skills_map = {}
        for item in skills:
            if isinstance(item, dict) and item.get("name"):
                skills_map[item.get("name")] = item
        return skills_map

    def _get_skill_schema(self, skill_name: str):
        if not skill_name:
            return None
        return self.full_skills_map.get(skill_name)

    def _read_json(self, path):
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return {}


def run_executor_terminal_test():
    """
    终端测试入口：用户输入问题 -> 规划器生成计划 -> 执行器执行计划。
    """
    planner = AgentPlanner()
    executor = AgentExecutor()

    print("执行器测试模式。")
    user_text = input("请输入任务：").strip()
    if not user_text:
        user_text = "在桌面新建一个文件夹"
        print(f"用户：{user_text}")

    print("\n规划思考：")
    plan_json = planner.plan_and_stream_thinking(user_text)
    #print(json.dumps(plan_json, ensure_ascii=False, indent=2))
    print("\n执行结果：")
    result = executor.excute_plan_stream(plan_json)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    run_executor_terminal_test()

