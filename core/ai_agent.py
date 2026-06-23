"""
模块职责：
1) 提供上下文记忆、技能提示词、底层职责提示词。
2) 对外暴露清晰的核心调用接口，供上层 Agent 复用。
"""

import sys
import os
import json
import uuid
import types
from datetime import datetime

# 将项目根目录加入 sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from core.llm_client import call_llm

try:
    from ai_tools import ai_statistics
except ImportError:
    class MockStats:
        """
        统计模块缺失时的降级实现。
        """

        def calculate_history_stats(self):
            """
            返回空统计结果，确保聊天逻辑可运行。
            """
            return {"total_completed": 0, "total_uncompleted": 0}

    ai_statistics = MockStats()

try:
    from tools import token_cal
except ImportError:
    class MockTokenCal:
        def get_compact_memory_summary(self):
            return ""
    token_cal = MockTokenCal()

try:
    from ai_tools import skill_registry
except ImportError:
    skill_registry = None


class AIAgent:
    """
    AI 历史数据分析与聊天代理。
    """

    def __init__(self, memory_path=None, max_history=20):
        """
        初始化代理实例并设置记忆存储。
        """
        self.core_ai_load_error = None
        self.tool_executed_in_last_chat = False
        self.max_history = max_history
        self.memory_path = memory_path or os.path.join(
            project_root, "core", "core_data", "core_chat_memory.json"
        )
        self.skills_metadata_path = os.path.join(
            project_root, "ai_tools", "skills_metadata.json"
        )
        self.skills_metadata_brief_path = os.path.join(
            project_root, "ai_tools", "skills_metadata_brief.json"
        )
        self.full_skills_map = self._load_full_skills_map()
        self._ensure_memory_file()
        self._ensure_skills_brief_file()

    def get_system_prompt(self):
        """
        生成系统提示词：底层职责 + 技能提示词 + 任务统计。
        """
        return self._build_system_prompt()

    def chat(self, text, stream=True):
        """
        UI 对话入口：保持流式输出，同时记录上下文。
        """
        messages = self._build_messages(text)
        if stream:
            return self._stream_and_record(messages, text)
        response_text = self._read_llm_response(
            call_llm(messages=messages, stream=False)
        )
        self._append_memory(text, response_text)
        return response_text

    def call_core(self, text, stream=False, max_tool_steps=3, record_memory=True, use_memory=True):
        """
        对外核心接口：支持工具调用与上下文记忆。
        返回结构：
        {
            "response": "最终回复文本",
            "tool_calls": [
                {"name": "skill_name", "arguments": {...}, "result": {...}}
            ]
        }
        """
        if stream:
            if record_memory:
                return self.chat(text, stream=True)
            messages = self._build_messages(text, use_memory=use_memory)
            return call_llm(messages=messages, stream=True)

        messages = self._build_messages(text, use_memory=use_memory)
        tool_calls = []
        response_text = ""

        for _ in range(max_tool_steps + 1):
            response_text = self._read_llm_response(
                call_llm(messages=messages, stream=False)
            )
            parsed_calls = self._extract_tool_calls(response_text)
            if not parsed_calls:
                if record_memory:
                    self._append_memory(text, response_text)
                return {"response": response_text, "tool_calls": tool_calls}

            for call in parsed_calls:
                call = self._enrich_tool_call_arguments(call, text)
                result = self._execute_skill_call(call)
                tool_calls.append({
                    "name": call.get("name"),
                    "arguments": call.get("arguments", {}),
                    "result": result
                })
                self.tool_executed_in_last_chat = True
                messages.append({"role": "assistant", "content": response_text})
                messages.append({
                    "role": "system",
                    "content": f"TOOL_RESULT: {json.dumps(result, ensure_ascii=False)}"
                })

        if record_memory:
            self._append_memory(text, response_text)
        return {"response": response_text, "tool_calls": tool_calls}

    def clear_context(self):
        """
        清空对话记忆文件。
        """
        self._save_json(self.memory_path, [])

    def _ensure_memory_file(self):
        """
        确保存储目录与记忆文件存在。
        """
        memory_dir = os.path.dirname(self.memory_path)
        if not os.path.exists(memory_dir):
            os.makedirs(memory_dir, exist_ok=True)
        if not os.path.exists(self.memory_path):
            self._save_json(self.memory_path, [])

    def _load_memory(self):
        """
        读取对话记忆列表。
        """
        data = self._read_json(self.memory_path, default=[])
        return data if isinstance(data, list) else []

    def _append_memory(self, question, response):
        """
        追加一条对话记录。
        """
        records = self._load_memory()
        records.append({
            "dialog_id": str(uuid.uuid4()),
            "question": question,
            "response": response,
            "time": datetime.now().isoformat()
        })
        self._save_json(self.memory_path, records)

    def _build_messages(self, user_text, use_memory=True):
        """
        组合系统提示词与历史上下文消息。
        """
        system_prompt = self._build_system_prompt()
        messages = [{"role": "system", "content": system_prompt}]

        if use_memory:
            history = self._load_memory()
            if self.max_history and len(history) > self.max_history:
                history = history[-self.max_history:]

            for record in history:
                question = str(record.get("question", "")).strip()
                answer = str(record.get("response", "")).strip()
                if question:
                    messages.append({"role": "user", "content": question})
                if answer:
                    messages.append({"role": "assistant", "content": answer})

        messages.append({"role": "user", "content": user_text})
        return messages

    def _build_system_prompt(self):
        """
        汇总底层职责、技能提示词与统计信息，实时获取当前时间。
        """
        base_prompt = self._build_base_responsibility_prompt()
        skills_prompt = self._build_skills_prompt()
        stats_prompt = self._build_stats_prompt()
        current_time = datetime.now().isoformat()
        return f"{base_prompt}\n\n{skills_prompt}\n\n{stats_prompt}\n\n[当前时间：{current_time}]" 

    def _build_base_responsibility_prompt(self):
        """
        构建底层职责提示词（100 词以内中文）。
        """
        return (
            "你是桌面任务与文件助手，负责理解用户意图、回答问题、"
            "必要时调用技能完成任务，并返回清晰结果；保持安全、简洁、准确。"
            "你有上下文记忆，但只能回忆起过去有限时间内的对话记录，不能回忆起更早的内容。"
        )
    
    def _build_stats_prompt(self):
        """
        生成任务统计提示词。
        """
        stats_data = ai_statistics.calculate_history_stats()
        total_tasks = stats_data.get("total_completed", 0) + stats_data.get("total_uncompleted", 0)
        completed_tasks = stats_data.get("total_completed", 0)
        pending_tasks = stats_data.get("total_uncompleted", 0)
        task_summary = f"[当前任务统计：总计 {total_tasks}，已完成 {completed_tasks}，未完成 {pending_tasks}]"
        token_summary = token_cal.get_compact_memory_summary()
        if token_summary:
            return f"{task_summary}\n{token_summary}"
        return task_summary

    def _build_skills_prompt(self):
        """
        构建技能提示词系统，明确何时调用技能与调用格式。
        """
        metadata = self._read_json(self.skills_metadata_brief_path, default={})
        skills = metadata.get("skills", []) if isinstance(metadata, dict) else []
        system_instruction = metadata.get("system_instruction", "") if isinstance(metadata, dict) else ""
        skills_text = self._format_brief_skills_list(skills)

        tool_protocol = (
            "当需要调用技能时，请只输出严格 JSON："
            "{\"action\": \"call_skill\", \"name\": \"技能名\", \"arguments\": {参数}}。"
            "如需多个技能，输出 {\"action\": \"call_skill\", \"tool_calls\": [..]}。"
            "无须调用时输出正常回答。"
        )

        if system_instruction:
            return f"{system_instruction}\n\n{tool_protocol}\n\n[技能清单]\n{skills_text}"
        return f"{tool_protocol}\n\n[技能清单]\n{skills_text}"

    def _format_skills_list(self, skills):
        """
        将技能元数据整理成简洁文本。
        """
        lines = []
        for skill in skills:
            name = skill.get("name", "未命名")
            description = skill.get("description", "")
            required = skill.get("required", [])
            parameters = skill.get("parameters", {})
            line = (
                f"- {name}: {description} | required={required} | params="
                f"{json.dumps(parameters, ensure_ascii=False)}"
            )
            lines.append(line)
        return "\n".join(lines) if lines else "- 暂无技能定义"

    def _format_brief_skills_list(self, skills):
        lines = []
        for skill in skills:
            name = skill.get("name", "未命名")
            description = skill.get("description", "")
            line = f"- {name}: {description}"
            lines.append(line)
        return "\n".join(lines) if lines else "- 暂无技能定义"

    def _stream_and_record(self, messages, question):
        """
        流式返回模型输出，并在结束后写入记忆。
        """
        response_stream = call_llm(messages=messages, stream=True)
        if not isinstance(response_stream, types.GeneratorType):
            response_text = self._read_llm_response(response_stream)
            self._append_memory(question, response_text)
            def _single():
                yield response_text
            return _single()

        def _generator():
            chunks = []
            for chunk in response_stream:
                if chunk is None:
                    continue
                chunk_text = str(chunk)
                chunks.append(chunk_text)
                yield chunk_text
            self._append_memory(question, "".join(chunks))

        return _generator()

    def _extract_tool_calls(self, text):
        """
        从回复中解析技能调用 JSON。
        """
        if not text:
            return []

        parsed = self._try_parse_json(text)
        if not parsed:
            return []

        if isinstance(parsed, dict):
            if parsed.get("action") == "call_skill" and parsed.get("tool_calls"):
                return [self._normalize_call(item) for item in parsed.get("tool_calls", [])]
            if parsed.get("action") == "call_skill" and parsed.get("name"):
                return [self._normalize_call(parsed)]
        if isinstance(parsed, list):
            return [self._normalize_call(item) for item in parsed]

        return []

    def _normalize_call(self, item):
        """
        规范化技能调用结构。
        """
        if not isinstance(item, dict):
            return {"name": None, "arguments": {}}
        return {
            "name": item.get("name"),
            "arguments": item.get("arguments", {})
        }

    def _execute_skill_call(self, call):
        """
        执行单个技能调用并返回结果。
        """
        if not skill_registry:
            return {"status": "error", "message": "技能注册模块不可用"}

        skill_name = call.get("name")
        arguments = call.get("arguments", {})
        if not skill_name:
            return {"status": "error", "message": "缺少技能名称"}

        func = skill_registry.get_skill_function(skill_name)
        if not func:
            return {"status": "error", "message": f"未注册技能：{skill_name}"}

        try:
            normalized_arguments = skill_registry.normalize_skill_arguments(skill_name, arguments)
            return func(**normalized_arguments) if isinstance(normalized_arguments, dict) else func(normalized_arguments)
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def _load_full_skills_map(self):
        metadata = self._read_json(self.skills_metadata_path, default={})
        skills = metadata.get("skills", []) if isinstance(metadata, dict) else []
        skills_map = {}
        for item in skills:
            if isinstance(item, dict) and item.get("name"):
                skills_map[item.get("name")] = item
        return skills_map

    def _get_skill_schema(self, skill_name):
        if not skill_name:
            return None
        return self.full_skills_map.get(skill_name)

    def _enrich_tool_call_arguments(self, call, user_text):
        if not isinstance(call, dict):
            return call
        skill_name = call.get("name")
        if not skill_name:
            return call
        schema = self._get_skill_schema(skill_name)
        if not isinstance(schema, dict):
            return call
        required = schema.get("required", [])
        if not required:
            return call
        arguments = call.get("arguments", {}) if isinstance(call.get("arguments"), dict) else {}
        missing = [key for key in required if not arguments.get(key)]
        if not missing:
            return call
        prompt = (
            "你需要为技能调用补全参数。"
            "\n请严格根据技能参数定义输出参数，不要猜测不存在的字段。"
            "\n只输出严格 JSON：{\"action\":\"call_skill\",\"name\":\"技能名\",\"arguments\":{参数}}。"
            f"\n\n[用户问题]\n{user_text}"
            f"\n\n[技能名称]\n{skill_name}"
            f"\n\n[技能参数定义]\n{json.dumps(schema, ensure_ascii=False)}"
            f"\n\n[已有参数]\n{json.dumps(arguments, ensure_ascii=False)}"
        )
        messages = [
            {"role": "system", "content": self._build_base_responsibility_prompt()},
            {"role": "user", "content": prompt}
        ]
        response_text = self._read_llm_response(call_llm(messages=messages, stream=False))
        parsed_calls = self._extract_tool_calls(response_text)
        if parsed_calls:
            enriched = parsed_calls[0]
            if enriched.get("name") == skill_name and isinstance(enriched.get("arguments"), dict):
                call["arguments"] = enriched.get("arguments", {})
        return call

    def _try_parse_json(self, text):
        """
        尝试从文本中解析 JSON。
        """
        raw = text.strip()
        try:
            return json.loads(raw)
        except Exception:
            pass

        if "{" in raw and "}" in raw:
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
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

    def _read_json(self, path, default=None):
        """
        安全读取 JSON 文件。
        """
        if not os.path.exists(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return default

    def _ensure_skills_brief_file(self):
        metadata = self._read_json(self.skills_metadata_path, default={})
        skills = metadata.get("skills", []) if isinstance(metadata, dict) else []
        brief_skills = []
        for skill in skills:
            name = skill.get("name")
            if not name:
                continue
            brief_skills.append({
                "name": name,
                "description": skill.get("description", "")
            })

        if not brief_skills:
            return

        brief_data = {"skills": brief_skills}
        existing = self._read_json(self.skills_metadata_brief_path, default={})
        existing_skills = existing.get("skills", []) if isinstance(existing, dict) else []
        if existing_skills != brief_skills:
            self._save_json(self.skills_metadata_brief_path, brief_data)

    def _save_json(self, path, data):
        """
        安全保存 JSON 文件。
        """
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    agent = AIAgent()
    print("测试 AIAgent...")
    for chunk in agent.chat("你能做什么？", stream=True):
        print(chunk, end="", flush=True)
