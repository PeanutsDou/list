"""
模块职责：
1) 调用底层 AI 生成任务规划 JSON。
2) 对外仅输出规划的思考过程文本。
3) 提供终端测试入口，便于独立验证。
"""

import os
import sys
import json
import time
import types

# 将项目根目录加入 sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from core.llm_client import call_llm
from core.ai_agent import AIAgent


class AgentPlanner:
    """
    规划器：根据用户问题生成执行计划 JSON，并输出思考过程。
    """

    def __init__(self):
        """
        初始化规划器。
        """
        self.agent = AIAgent()

    def plan_and_stream_thinking(self, user_text, execution_history=None):
        """
        生成规划并以流式方式输出思考过程文本（真流式）。
        execution_history: 上一轮的执行结果（包含 excute plan 和 step results），用于前置审查。
        """
        system_prompt = self._build_system_prompt()
        
        # 如果有执行历史，将其注入到用户输入上下文中
        final_user_text = user_text
        if execution_history:
            history_str = json.dumps(execution_history, ensure_ascii=False, indent=2)
            final_user_text = (
                f"{user_text}\n\n"
                f"== [前置审查提醒] ==\n"
                f"这是上一轮的执行结果，请仔细检查 'step results' 字段。\n"
                f"1. 如果某个步骤显示 'success': true，说明该步骤已完成，请**不要**在新的规划中包含该步骤，避免重复操作（如重复创建文件）。\n"
                f"2. 如果文件已存在，请直接读取或更新，不要尝试再次创建。\n"
                f"3. 仅规划未完成、失败或后续的步骤。\n"
                f"====================\n"
                f"{history_str}"
            )
        
        # 允许规划器调用信息获取类技能
        # 使用 call_core 接口，允许模型在生成最终 JSON 前先调用工具
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": final_user_text}
        ]
        
        # 注意：这里我们原本是直接 call_llm 生成 JSON。
        # 为了支持“规划器调用技能获取信息”，我们需要改用 agent.call_core 的逻辑，或者在这里手动处理 tool_calls。
        # 鉴于 AgentPlanner 原本是流式输出 thinking，如果引入 tool_calls，流程会变得复杂（thinking -> tool -> thinking -> json）。
        # 我们可以采用一种简化的方式：
        # 让模型在 thinking 阶段如果需要信息，可以输出特定的 tool call 标记，我们截获并执行，然后将结果喂回。
        # 但考虑到架构改动较大，且 call_core 已经封装好了 tool loop。
        # 我们可以复用 call_core，但要求模型最终输出符合 json_spec 的内容。
        
        # 方案修正：直接使用 call_llm，但允许模型输出 tool_calls。
        # 如果模型输出了 tool_calls，我们在内部执行并追加结果，直到模型输出最终 JSON。
        
        current_messages = messages.copy()
        max_turns = 3 # 限制信息获取轮数
        
        for _ in range(max_turns + 1):
            response_generator = call_llm(messages=current_messages, stream=True)
            
            full_response = ""
            cursor = 0
            content_start_idx = -1
            stop_printing = False
            
            # 临时存储可能得 tool calls
            collected_tool_calls = []
            is_tool_call = False
            
            # 流式处理
            if not isinstance(response_generator, types.GeneratorType):
                 # 非流式处理 (fallback)
                 full_response = str(response_generator)
                 # 检查是否有 tool_calls (取决于 llm_client 实现，通常非流式返回 content 或 structure)
                 # 这里假设 call_llm 如果 stream=True 总是返回 generator
                 pass 
            else:
                for chunk in response_generator:
                    if not chunk: continue
                    chunk_str = str(chunk)
                    full_response += chunk_str
                    
                    # 检查是否是 JSON 格式的 tool call (如果模型直接输出 JSON)
                    # 或者 call_llm 底层已经处理了 tool call 结构？ 
                    # 通常 call_llm stream=True 返回的是 delta content。
                    # 如果是 function call，delta 中会有 tool_calls 字段。
                    # 但目前的 call_llm 似乎返回的是 str (content)。
                    # 我们假设模型会直接在文本中输出 JSON 格式的 tool call，或者我们依赖 system prompt 里的定义。
                    
                    # 按照 agent_planner 原有逻辑，它是流式打印 thinking。
                    # 我们保留这个逻辑。
                    
                    # 尝试定位 "thinking": " ... "
                    if content_start_idx == -1:
                        idx = full_response.find('"thinking":')
                        if idx != -1:
                            q_idx = full_response.find('"', idx + 11)
                            if q_idx != -1:
                                content_start_idx = q_idx + 1
                                cursor = content_start_idx
                    
                    if content_start_idx != -1 and not stop_printing:
                        i = cursor
                        while i < len(full_response):
                            char = full_response[i]
                            if char == '\\':
                                i += 2
                                continue
                            if char == '"':
                                segment = full_response[cursor:i]
                                print(self._unescape_json_string(segment), end="", flush=True)
                                cursor = i
                                stop_printing = True # 思考结束
                                break
                            i += 1
                        if not stop_printing and i >= len(full_response) and cursor < len(full_response):
                             if not full_response.endswith('\\'):
                                segment = full_response[cursor:]
                                print(self._unescape_json_string(segment), end="", flush=True)
                                cursor = len(full_response)

            print("") # 换行

            # 检查 full_response 是否包含 tool_calls (根据 system prompt 里的定义)
            # 或者它是否是最终的 plan json
            plan_json = self._extract_plan_json(full_response)
            
            # 检查是否有显式的 tool action (我们 system prompt 里定义了 call_skill 格式)
            # 但这里我们主要期望它输出 plan json。
            # 如果我们想让它先调用工具，它应该输出一个只包含 action: call_skill 的 JSON，而不是完整的 plan。
            
            # 让我们解析一下看看是不是 skill call
            parsed = self._try_parse_json(full_response)
            if isinstance(parsed, dict) and parsed.get("action") == "call_skill":
                # 执行技能
                skill_name = parsed.get("name")
                args = parsed.get("arguments", {})
                print(f"\n[规划器] 正在调用信息获取技能: {skill_name}...")
                
                # 权限检查：只允许 read 类技能
                if not self._is_safe_read_skill(skill_name):
                    result = {"status": "error", "message": f"规划阶段禁止调用修改类技能 '{skill_name}'，请仅使用读取/查询类技能。"}
                else:
                    # 执行
                    # 复用 agent 的 _execute_skill_call
                    call_struct = {"name": skill_name, "arguments": args}
                    result = self.agent._execute_skill_call(call_struct)
                
                print(f"[规划器] 技能返回: {str(result)[:200]}...")
                
                # 将结果追加到 messages
                current_messages.append({"role": "assistant", "content": full_response})
                current_messages.append({
                    "role": "system", 
                    "content": f"TOOL_RESULT: {json.dumps(result, ensure_ascii=False)}\n请根据以上信息继续规划，或者再次调用技能获取更多信息。"
                })
                continue # 进入下一轮循环
            
            # 如果不是 tool call，或者是最终 plan，就返回
            return plan_json

        return self._extract_plan_json(full_response)

    def _is_safe_read_skill(self, skill_name):
        """
        检查是否是安全的读取类技能。
        """
        if not skill_name: return False
        name = skill_name.lower()
        # 允许的动词前缀
        allow_prefixes = ["read_", "get_", "list_", "search_", "query_", "check_"]
        # 显式禁止的关键词
        deny_keywords = ["delete", "remove", "update", "write", "create", "append", "set_", "move_", "copy_", "upload", "push", "merge"]
        
        for kw in deny_keywords:
            if kw in name:
                return False
        
        for prefix in allow_prefixes:
            if name.startswith(prefix):
                return True
        
        return False

    def _unescape_json_string(self, text):
        """
        简单的反转义处理，将 JSON 字符串中的转义序列转换为实际字符。
        """
        # 常见转义
        return text.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\').replace('\\t', '\t')


    def _build_system_prompt(self):
        """
        构建规划器系统提示词。
        """
        base_instruction = (
            "你是任务规划器，只负责理解用户需求并生成规划 JSON。"
            "必须输出严格 JSON，不要输出多余文本。"
            "一定要注意，用户提出的需求绝大多数时候是笼统的，你要基于你的上下文推断出准确的解决方案。"
            "你必须结合历史对话与当前问题，保持需求连续，不要忽略上一轮已获取的信息。"
            "**前置审查机制**：在规划前，请仔细审查历史步骤结果（如果存在）。"
            "如果发现某些步骤已经成功执行（例如文件已创建），则**不要**在新的规划中重复这些步骤，而是直接从中断处继续，或根据最新状态调整后续计划。"
            "**信息获取权限**：你可以调用读取/查询类的技能（如 read_*, search_*, get_*）来获取环境信息，辅助你制定更准确的计划。"
            "但**绝对禁止**调用具有副作用的技能（如 create_*, update_*, delete_*, write_* 等），这些必须留给执行器执行。"
        )

        json_spec = (
            "JSON 字段必须包含："
            "1) \"is skills\"：布尔值，表示是否需要调用技能。"
            "2) \"description\"：列表，拆解后的用户需求。"
            "3) \"excute plan\"：列表，每项包含 step ，desc 与 skill，"
            "其中 step 为执行的步骤序号，desc 为对任务的详细描述，skill 为需要调用的技能名称以及技能的参数。"
            "skill 字段必须包含技能名称与需要的参数，参数必须是 JSON 格式。"
            "4) \"thinking\"：文字，逐步建立解决方案的思考过程,专门针对excute plan中的每个步骤都要标注好步骤序号并换行显示。"
            "当不需要调用技能时，description 与 excute plan 可为空列表，但 thinking 仍需完整。"
        )

        return f"{self.agent.get_system_prompt()}\n\n{base_instruction}\n{json_spec}"

    def _extract_plan_json(self, text):
        """
        从文本中提取规划 JSON。
        """
        parsed = self._try_parse_json(text)
        if isinstance(parsed, dict):
            return parsed
        return {
            "is skills": False,
            "description": [],
            "excute plan": [],
            "thinking": str(text or "")
        }

    def _try_parse_json(self, text):
        """
        尝试解析 JSON。
        """
        if not text:
            return None
        raw = text.strip()
        try:
            return json.loads(raw)
        except Exception:
            pass
        if "{" in raw and "}" in raw:
            start = raw.find("{")
            end = raw.rfind("}")
            if end > start:
                snippet = raw[start:end + 1]
                try:
                    return json.loads(snippet)
                except Exception:
                    return None
        return None

    def _read_llm_response(self, response):
        """
        读取非流式或流式响应为字符串。
        """
        if isinstance(response, str):
            return response
        if isinstance(response, types.GeneratorType):
            chunks = []
            while True:
                try:
                    chunk = next(response)
                    if chunk:
                        chunks.append(str(chunk))
                except StopIteration as exc:
                    if exc.value:
                        chunks.append(str(exc.value))
                    break
            return "".join(chunks)
        return "" if response is None else str(response)

def run_planner_terminal_test():
    """
    终端测试入口：输入问题，输出思考过程。
    """
    planner = AgentPlanner()
    print("规划器测试模式。")
    user_text = "在桌面新建三个文件夹，然后删除其中两个，再在桌面上找到任意三个文件/文件夹，放到剩下的那个新建文件夹里"
    print(f"用户：{user_text}")
    print("\n规划思考：")
    
    # 调用流式输出方法
    result = planner.plan_and_stream_thinking(user_text)
    # 把json整体打印出来
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    run_planner_terminal_test()
