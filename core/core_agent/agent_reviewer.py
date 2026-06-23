"""
执行审查器：调用 ai_agent 里的 LLM 对执行结果进行审查与总结。
核心职责：
1) 若 is skills 为 False，直接总结回答用户问题。
2) 若 is skills 为 True，逐步核查执行结果，在每一步新增 check 字段。
3) 若存在失败步骤，新增 error 与 is back 字段，给出可回溯的错误报告。
4) 若审查通过或超过回溯次数，汇总执行结果并给出最终回答与建议。
"""

import os
import sys
import json
from typing import Any, Dict, List, Tuple

# 将项目根目录加入 sys.path，保证跨目录导入稳定
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from core.ai_agent import AIAgent
from core.llm_client import call_llm


class AgentReviewer:
    """
    执行审查器：校验执行结果并调用 LLM 汇总答案或错误报告。
    """

    def __init__(self):
        """
        初始化审查器，加载底层 AIAgent。
        """
        self.agent = AIAgent()

    def review_execute_result(self, execute_json: Dict[str, Any], user_text: str,
                              max_rounds: int, current_round: int) -> Dict[str, Any]:
        """
        审查执行结果，返回审查状态、更新后的 JSON 与最终回答流式文本。
        """
        normalized = self._normalize_execute_json(execute_json)
        if not normalized.get("is skills", False):
            final_answer = self._build_direct_answer(user_text, normalized)
            return {
                "review_passed": True,
                "review_json": normalized,
                "final_answer": final_answer,
                "need_replan": False
            }

        failed_steps = self._check_steps(normalized)
        review_passed = len(failed_steps) == 0
        normalized["review_passed"] = review_passed

        if review_passed:
            final_answer = self._build_success_answer(user_text, normalized)
            return {
                "review_passed": True,
                "review_json": normalized,
                "final_answer": final_answer,
                "need_replan": False
            }

        error_report = self._build_error_report(user_text, normalized, failed_steps)
        normalized["error"] = error_report
        normalized["is back"] = True

        if current_round >= max_rounds:
            final_answer = self._build_fail_answer(user_text, normalized)
            return {
                "review_passed": False,
                "review_json": normalized,
                "final_answer": final_answer,
                "need_replan": False
            }

        return {
            "review_passed": False,
            "review_json": normalized,
            "final_answer": self._empty_stream(),
            "need_replan": True
        }

    def _check_steps(self, execute_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        核查每个执行步骤是否成功，并写入 check 字段。
        """
        failed_steps = []
        plan_steps = execute_json.get("excute plan", [])
        if not isinstance(plan_steps, list):
            return [{"step": None, "reason": "excute plan 结构错误"}]

        for step in plan_steps:
            check_result, reason = self._analyze_step_result(step)
            step["check"] = check_result
            if not check_result:
                failed_steps.append({
                    "step": step.get("step"),
                    "desc": step.get("desc"),
                    "reason": reason
                })

        return failed_steps

    def _analyze_step_result(self, step: Dict[str, Any]) -> Tuple[bool, str]:
        """
        根据 step results 判定当前步骤是否成功。
        """
        if not isinstance(step, dict):
            return False, "步骤数据格式错误"

        step_results = step.get("step results")
        if not isinstance(step_results, dict):
            return False, "缺少 step results"

        if step_results.get("success") is False:
            return False, step_results.get("message", "步骤执行失败")

        data = step_results.get("data")
        if isinstance(data, list):
            for item in data:
                result = item.get("result") if isinstance(item, dict) else None
                if isinstance(result, dict) and result.get("success") is False:
                    return False, result.get("message", "技能执行失败")

        return True, "执行成功"

    def _build_direct_answer(self, user_text: str, execute_json: Dict[str, Any]):
        """
        当不需要技能时，返回流式回答。
        """
        prompt = (
            "你是审查总结助手，需要根据用户问题给出简洁准确的回答。"
            "当前任务无需技能执行，请直接回复用户问题。"
            f"\n\n[用户问题]\n{user_text}\n"
            f"\n[执行信息]\n{self._safe_json(execute_json)}"
        )
        return self._call_llm_stream(prompt)

    def _build_success_answer(self, user_text: str, execute_json: Dict[str, Any]):
        """
        当执行通过审查时，调用 LLM 返回自然语言回答。
        """
        prompt = (
            "你是任务总结助手。用户提出了一个请求，任务已成功执行完成。"
            "请根据下面的执行结果，用自然语言回答用户的问题或总结任务完成情况。"
            "不要输出 JSON、程序化的调试信息（如 success=True）或代码片段。"
            "请直接输出给用户的最终回复，语气自然、简洁。"
            f"\n\n[用户问题]\n{user_text}\n"
            f"\n[执行结果]\n{self._safe_json(execute_json)}"
        )
        return self._call_llm_stream(prompt)

    def _build_error_report(self, user_text: str, execute_json: Dict[str, Any],
                            failed_steps: List[Dict[str, Any]]) -> str:
        """
        当执行失败时，调用 LLM 生成错误报告。
        """
        prompt = (
            "你是执行审查助手，需要根据失败步骤生成错误报告。"
            "请明确指出失败原因，并回溯到用户需求。"
            f"\n\n[用户问题]\n{user_text}\n"
            f"\n[失败步骤]\n{self._safe_json(failed_steps)}\n"
            f"\n[执行结果]\n{self._safe_json(execute_json)}"
        )
        return self._call_llm_text(prompt)

    def _build_fail_answer(self, user_text: str, execute_json: Dict[str, Any]):
        """
        当超过最大回溯次数仍失败时，返回流式总结与建议。
        """
        prompt = (
            "你是最终总结助手，任务多次回溯仍失败。"
            "请结合错误报告与用户需求给出总结与建议。"
            f"\n\n[用户问题]\n{user_text}\n"
            f"\n[执行结果]\n{self._safe_json(execute_json)}"
        )
        return self._call_llm_stream(prompt)

    def _call_llm_text(self, prompt: str) -> str:
        """
        调用底层 LLM 返回纯文本回答。
        """
        result = self.agent.call_core(
            prompt,
            stream=False,
            max_tool_steps=0,
            record_memory=False,
            use_memory=False
        )
        if isinstance(result, dict):
            return str(result.get("response", ""))
        return str(result or "")

    def _call_llm_stream(self, prompt: str):
        messages = [
            {"role": "system", "content": self.agent.get_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        response_stream = call_llm(messages=messages, stream=True)
        if isinstance(response_stream, str):
            def _single():
                yield response_stream
            return _single()
        def _generator():
            for chunk in response_stream:
                if chunk is None:
                    continue
                yield str(chunk)
        return _generator()

    def _single_stream(self, text: str):
        def _generator():
            if text:
                yield str(text)
        return _generator()

    def _empty_stream(self):
        def _generator():
            if False:
                yield ""
        return _generator()

    def _build_success_text(self, user_text: str, execute_json: Dict[str, Any]) -> str:
        steps = execute_json.get("excute plan", [])
        lines = []
        if user_text:
            lines.append(f"任务已完成：{user_text}")
        else:
            lines.append("任务已完成。")
        if isinstance(steps, list):
            for step in steps:
                if not isinstance(step, dict):
                    continue
                desc = str(step.get("desc", "")).strip()
                step_results = step.get("step results") if isinstance(step.get("step results"), dict) else {}
                message = str(step_results.get("message", "")).strip()
                if desc and message:
                    lines.append(f"- {desc}：{message}")
                elif desc:
                    lines.append(f"- {desc}")
                elif message:
                    lines.append(f"- {message}")
                data = step_results.get("data")
                if isinstance(data, list):
                    for item in data:
                        name = ""
                        result = None
                        if isinstance(item, dict):
                            name = str(item.get("name", "")).strip()
                            result = item.get("result")
                        summary = self._summarize_result(result)
                        if name and summary:
                            lines.append(f"- {name}：{summary}")
                        elif summary:
                            lines.append(f"- {summary}")
        return "\n".join(lines) if lines else ("任务已完成。" if not user_text else f"任务已完成：{user_text}")

    def _summarize_result(self, result: Any) -> str:
        if result is None:
            return ""
        if isinstance(result, dict):
            parts = []
            for i, (k, v) in enumerate(result.items()):
                if i >= 4:
                    break
                if isinstance(v, list):
                    parts.append(f"{k}={len(v)}项")
                elif isinstance(v, dict):
                    parts.append(f"{k}={len(v)}键")
                else:
                    text = str(v)
                    if len(text) > 60:
                        text = text[:57] + "..."
                    parts.append(f"{k}={text}")
            return "；".join(parts)
        if isinstance(result, list):
            count = len(result)
            previews = []
            for i, v in enumerate(result[:3]):
                if isinstance(v, dict):
                    keys = list(v.keys())[:3]
                    previews.append(",".join(keys))
                else:
                    text = str(v)
                    if len(text) > 40:
                        text = text[:37] + "..."
                    previews.append(text)
            if previews:
                return f"{count}项；示例：{ ' | '.join(previews) }"
            return f"{count}项"
        text = str(result)
        return text[:80] + ("..." if len(text) > 80 else "")

    def _normalize_execute_json(self, execute_json: Any) -> Dict[str, Any]:
        """
        规范化执行结果结构，确保关键字段可用。
        """
        if not isinstance(execute_json, dict):
            return {
                "is skills": False,
                "description": [],
                "excute plan": [],
                "thinking": str(execute_json or "")
            }
        execute_json.setdefault("is skills", False)
        execute_json.setdefault("description", [])
        execute_json.setdefault("excute plan", [])
        execute_json.setdefault("thinking", "")
        return execute_json

    def _safe_json(self, data: Any) -> str:
        """
        安全将数据序列化为 JSON 字符串。
        """
        try:
            return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            return str(data)
