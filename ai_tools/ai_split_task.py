import sys
import os
import json
import re
import types

# 添加项目根目录到 sys.path，以便导入 core 模块
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from core.llm_client import call_llm


def _read_llm_response(response):
    if isinstance(response, str):
        return response
    if isinstance(response, types.GeneratorType):
        chunks = []
        while True:
            try:
                chunk = next(response)
                if chunk:
                    chunks.append(str(chunk))
            except StopIteration as e:
                if e.value:
                    chunks.append(str(e.value))
                break
        return "".join(chunks)
    if response is None:
        return ""
    return str(response)

def split_task(task_content):
    """
    使用 AI 将复杂的任务描述拆分为多个具体的子任务。
    
    Args:
        task_content (str): 原始任务描述
        
    Returns:
        list: 拆分后的任务列表 (strings)
    """
    if not task_content or not task_content.strip():
        return []

    system_prompt = """
    你是一个专业的项目经理和任务拆解专家。你的目标是将用户给出的一个复杂任务，拆解为多个具体的、可执行的、逻辑顺序合理的子任务。
    
    请遵循以下规则：
    1. 保持拆解后的任务简洁明了。
    2. 如果任务本身很简单不需要拆分，则稍微优化一下描述即可，返回包含该任务的列表。
    3. 输出必须是严格的 JSON 格式，是一个字符串列表。不要包含 markdown 代码块标记 (如 ```json ... ```)。
    4. 例如：["第一步：...", "第二步：...", "第三步：..."]
    """

    prompt = f"请将以下任务拆解为具体的工序清单：\n\n{task_content}"

    response = call_llm(prompt, system_prompt, stream=False)
    response = _read_llm_response(response)

    # 尝试解析 JSON
    try:
        # 有时候 LLM 会忍不住加 markdown 标记，这里做简单的清洗
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        
        cleaned_response = cleaned_response.strip()
        
        tasks = json.loads(cleaned_response)
        
        if isinstance(tasks, list):
            return [str(t) for t in tasks]
        else:
            # 如果返回的不是列表，尝试按行分割
            return [line.strip() for line in response.split('\n') if line.strip()]
            
    except json.JSONDecodeError:
        # 如果 JSON 解析失败，回退到按行分割或其他简单的启发式处理
        # 移除可能的空行和无关的说明文字
        lines = response.split('\n')
        tasks = []
        for line in lines:
            line = line.strip()
            # 过滤掉一些常见的非任务行
            if not line or line.startswith("```"):
                continue
            # 尝试去掉列表符号如 "1. ", "- "
            line = re.sub(r'^[\d]+\.\s*', '', line)
            line = re.sub(r'^-\s*', '', line)
            tasks.append(line)
        return tasks
    except Exception as e:
        return [f"AI 处理出错: {str(e)}", "原始任务保留: " + task_content]

if __name__ == "__main__":
    # 测试代码
    test_task = "帮我写一个贪吃蛇游戏，要用Python，界面好看一点"
    print("Testing split_task...")
    result = split_task(test_task)
    for t in result:
        print(f"- {t}")
