import os
import requests
import json
import sys

# 确保能导入 tools
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from tools import token_cal
    from tools.config_loader import get_llm_config
except ImportError:
    class _MockTokenCal:
        def record_usage(self, usage, session_id=None):
            return {"success": False, "reason": "token_cal_unavailable"}
        def get_active_session(self):
            return None
    token_cal = _MockTokenCal()
    def get_llm_config():
        return {}


def _record_usage_from_result(result):
    if not isinstance(result, dict):
        return
    usage = result.get("usage")
    if not isinstance(usage, dict):
        return
    token_cal.record_usage(usage)

def call_llm(prompt=None, system_prompt="You are a helpful assistant.", messages=None, stream=False):
    """
    调用 LLM API 处理 prompt。
    参数：
        prompt: 用户输入（如果提供了 messages，此参数会被忽略或作为最新一条用户消息追加）
        system_prompt: 系统提示词（如果提供 messages 且 messages[0] 为 system，则可能被忽略）
        messages: 完整的消息历史列表 [{"role": "user", "content": ...}, ...]
        stream: 是否使用流式输出
    """
    config = get_llm_config()
    
    api_key = config.get("api_key")
    model = config.get("model")
    base_url = config.get("base_url")

    if not all([api_key, model, base_url]):
        msg = "错误：缺少配置项（api_key、model 或 base_url），请检查 config.json。"
        if stream:
            yield msg
            return
        return msg

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 构造请求数据
    final_messages = []
    if messages:
        final_messages = messages
        # 如果提供了 prompt，追加为最新的一条用户消息
        if prompt:
             final_messages.append({"role": "user", "content": prompt})
    else:
        final_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

    data = {
        "model": model,
        "messages": final_messages,
        "stream": stream
    }

    # 确保 URL 是 chat completions 的完整路径
    if not base_url.endswith("/chat/completions"):
        if base_url.endswith("/"):
            api_url = base_url + "chat/completions"
        else:
            api_url = base_url + "/chat/completions"
    else:
        api_url = base_url

    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=30, stream=stream)
        response.raise_for_status()
        
        if stream:
            last_usage = None
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith("data: "):
                        content = line[6:]  # Remove "data: "
                        if content == "[DONE]":
                            break
                        try:
                            json_data = json.loads(content)
                            if isinstance(json_data, dict) and isinstance(json_data.get("usage"), dict):
                                last_usage = json_data.get("usage")
                            delta = json_data.get("choices", [{}])[0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except json.JSONDecodeError:
                            pass
            if last_usage:
                token_cal.record_usage(last_usage)
        else:
            result = response.json()
            _record_usage_from_result(result)
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                return f"Error: Unexpected response format: {result}"
            
    except requests.exceptions.RequestException as e:
        msg = f"HTTP 请求失败：{str(e)}"
        if stream:
            yield msg
        return msg
    except Exception as e:
        msg = f"错误：{str(e)}"
        if stream:
            yield msg
        return msg
