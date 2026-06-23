"""
对外统一 Agent 接口：负责串联规划器与执行器，并维护对话记忆。
"""

import os
import sys
import json
import queue
import threading
import contextlib
import types
from datetime import datetime, timedelta

# 将项目根目录加入 sys.path，保证跨目录导入稳定
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from core.ai_agent import AIAgent
from core.core_agent.agent_planner import AgentPlanner
from core.core_agent.agent_excuter import AgentExecutor
from core.core_agent.agent_reviewer import AgentReviewer


class _QueueWriter:
    """
    将输出写入队列与缓存，支持被 redirect_stdout 捕获。
    """

    def __init__(self, output_queue, buffer_list):
        """
        初始化输出写入器。
        """
        self.output_queue = output_queue
        self.buffer_list = buffer_list

    def write(self, text):
        """
        写入文本：同步进入缓存并推送到队列。
        """
        if not text:
            return
        chunk = str(text)
        self.buffer_list.append(chunk)
        self.output_queue.put(chunk)

    def flush(self):
        """
        flush 兼容接口。
        """
        return None


class AgentSession:
    """
    Agent 会话：统一对外流式输出，并维护对话记忆。
    """

    def __init__(self):
        """
        初始化会话，创建规划器、执行器与记忆代理。
        """
        self.planner = AgentPlanner()
        self.executor = AgentExecutor()
        self.reviewer = AgentReviewer()
        self.memory_agent = AIAgent()
        self.tool_executed_in_last_chat = False
        self.max_review_rounds = 3
        self.progress_start_token = "[[PROGRESS_START]]"
        self.progress_end_token = "[[PROGRESS_END]]"
        self.final_start_token = "[[FINAL_START]]"
        self.final_end_token = "[[FINAL_END]]"

    def clear_context(self):
        """
        清空对话记忆文件。
        """
        self.memory_agent.clear_context()

    def chat(self, text, stream=True):
        """
        对外聊天入口，支持流式输出与非流式输出。
        """
        if stream:
            return self._stream_chat(text)
        return self._run_turn_and_return(text)

    def _run_turn_and_return(self, user_text):
        """
        非流式执行一轮对话，返回完整文本。
        """
        output_queue = queue.Queue()
        buffer_list = []
        self._execute_turn(user_text, output_queue, buffer_list)
        return "".join(buffer_list)

    def _stream_chat(self, user_text):
        """
        流式执行一轮对话，实时返回输出片段。
        """
        output_queue = queue.Queue()
        buffer_list = []

        def _worker():
            self._execute_turn(user_text, output_queue, buffer_list)
            output_queue.put(None)

        threading.Thread(target=_worker, daemon=True).start()

        def _generator():
            while True:
                chunk = output_queue.get()
                if chunk is None:
                    break
                yield chunk

        return _generator()

    def _execute_turn(self, user_text, output_queue, buffer_list):
        """
        执行一轮对话流程：规划 -> 执行 -> 审查 -> 回答 -> 记忆写入。
        """
        writer = _QueueWriter(output_queue, buffer_list)
        try:
            with contextlib.redirect_stdout(writer):
                writer.write(self.progress_start_token)
                # 构造包含历史记忆的用户输入，保证规划阶段具备上下文
                enriched_text = self._build_enriched_user_text(user_text)
                final_answer = ""
                executed_plan = None

                for round_no in range(1, self.max_review_rounds + 1):
                    print(f"规划思考（第{round_no}轮）：")
                    # 将上一轮执行结果注入到规划器中，供前置审查机制使用
                    execution_history = None
                    if executed_plan:
                        execution_history = executed_plan
                    
                    plan_json = self.planner.plan_and_stream_thinking(enriched_text, execution_history)
                    print("\n执行结果：")
                    executed_plan = self.executor.excute_plan_stream(plan_json)
                    print("\n审查结果：")

                    review_result = self.reviewer.review_execute_result(
                        executed_plan, user_text, self.max_review_rounds, round_no
                    )
                    executed_plan = review_result.get("review_json", executed_plan)

                    review_summary = []
                    if isinstance(executed_plan, dict):
                        for step in executed_plan.get("excute plan", []) or []:
                            step_results = step.get("step results") if isinstance(step, dict) else None
                            review_summary.append({
                                "step": step.get("step") if isinstance(step, dict) else None,
                                "desc": step.get("desc") if isinstance(step, dict) else None,
                                "check": step.get("check") if isinstance(step, dict) else None,
                                "message": step_results.get("message") if isinstance(step_results, dict) else None
                            })
                    print(json.dumps(review_summary, ensure_ascii=False, indent=2))

                    if review_result.get("review_passed"):
                        final_answer = review_result.get("final_answer", "")
                        print("审查通过。")
                        break

                    error_report = executed_plan.get("error") if isinstance(executed_plan, dict) else None
                    if error_report:
                        print(error_report)
                    if not review_result.get("need_replan"):
                        final_answer = review_result.get("final_answer", "")
                        break

                    print("审查未通过，准备重新规划。")

                writer.write(self.progress_end_token)
                writer.write(self.final_start_token)
                if isinstance(final_answer, types.GeneratorType):
                    for chunk in final_answer:
                        writer.write(chunk)
                elif final_answer:
                    for idx in range(0, len(final_answer), 120):
                        writer.write(final_answer[idx: idx + 120])
                writer.write(self.final_end_token)
        except Exception as exc:
            error_text = f"执行失败：{str(exc)}"
            writer.write(error_text)
        finally:
            full_text = "".join(buffer_list)
            sanitized_text = self._sanitize_memory_text(full_text)
            self.memory_agent._append_memory(user_text, sanitized_text)
            self.tool_executed_in_last_chat = getattr(
                self.executor.agent, "tool_executed_in_last_chat", False
            )

    def _build_enriched_user_text(self, user_text):
        """
        将历史对话记忆注入到当前用户输入中，供规划阶段读取上下文。
        """
        history = self.memory_agent._load_memory()
        if not history:
            return user_text

        history_lines = []
        # 时间输出格式参考："time": "2026-02-17T00:56:02.771980"
        now_time = datetime.now()
        # 限定上下文历史时长为1小时
        history_duration = timedelta(hours=1)

        for record in history:
            question = str(record.get("question", "")).strip()
            response = str(record.get("response", "")).strip()
            time_text = str(record.get("time", "")).strip()
            # 限定将超出上下文历史时长的记录过滤掉，不注入
            if not time_text:
                continue
            try:
                record_time = datetime.fromisoformat(time_text)
            except Exception:
                try:
                    record_time = datetime.strptime(time_text, "%Y-%m-%d %H:%M:%S.%f")
                except Exception:
                    continue
            if record_time < now_time - history_duration:
                continue   
            if question:
                history_lines.append(f"用户：{question}")
            if response:
                history_lines.append(f"助手：{response}")

        if not history_lines:
            return user_text

        history_block = "\n".join(history_lines)
        return f"[历史对话]\n{history_block}\n\n[当前问题]\n{user_text}"

    def _sanitize_memory_text(self, text):
        """
        清理流式控制标记，避免污染对话记忆。
        """
        if not isinstance(text, str):
            return str(text or "")
        for token in [
            self.progress_start_token,
            self.progress_end_token,
            self.final_start_token,
            self.final_end_token
        ]:
            text = text.replace(token, "")
        return text


def run_agent_terminal():
    """
    终端测试入口：用户输入问题 -> 规划器生成计划 -> 执行器执行计划。
    """
    agent = AgentSession()

    print("执行器测试模式。")
    while True:
        user_text = input("请输入任务：").strip()
        if not user_text:
            user_text = "在桌面新建三个文件夹，然后删除其中两个，再在桌面上找到任意三个文件/文件夹，放到剩下的那个新建文件夹里"
            print(f"用户：{user_text}")

        for chunk in agent.chat(user_text, stream=True):
            print(chunk, end="", flush=True)
        print("")


if __name__ == "__main__":
    run_agent_terminal()
