
import os
import json
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from ai_files_tools.ai_files_read import resolve_target_path

DATA_FILE = os.path.join(os.path.dirname(__file__), "common_files.json")


def remove_common_file(path):
    normalized = _normalize_path(path)
    if not normalized:
        return {"success": False, "reason": "path_invalid", "message": "路径无效"}
    normalized_key = os.path.normcase(os.path.abspath(os.path.normpath(normalized)))
    data = _load_data()
    manual_before = list(data.get("manual", []))
    opens_before = data.get("opens", {})

    manual_after = [
        p for p in manual_before
        if os.path.normcase(os.path.abspath(os.path.normpath(p))) != normalized_key
    ]
    opens_after = {}
    removed_from_open = 0
    for date_str, items in opens_before.items():
        filtered = [
            p for p in items
            if os.path.normcase(os.path.abspath(os.path.normpath(p))) != normalized_key
        ]
        removed_from_open += max(0, len(items) - len(filtered))
        opens_after[date_str] = filtered

    data["manual"] = manual_after
    data["opens"] = opens_after
    _save_data(data)

    return {
        "success": True,
        "path": normalized,
        "removed_from_manual": len(manual_before) - len(manual_after),
        "removed_from_open": removed_from_open
    }


def remove_common_files_batch(paths_list):
    """
    批量移除常用文件记录。
    
    Args:
        paths_list (list): 文件路径列表。
    
    Returns:
        list: 每个操作的结果列表。
    """
    results = []
    if not isinstance(paths_list, list):
        return [{"success": False, "reason": "invalid_input", "message": "输入必须是列表"}]

    for path in paths_list:
        result = remove_common_file(path)
        result["input_path"] = path
        results.append(result)
    return results


def _normalize_path(path):
    """
    规范化路径：支持快捷方式解析。
    """
    if not path:
        return None
    
    # 优先解析快捷方式目标
    resolved = resolve_target_path(path)
    if not resolved:
        # 如果解析失败（比如文件不存在），至少规范化路径字符串
        raw_path = path.strip().strip("\"")
        resolved = os.path.abspath(os.path.normpath(raw_path))

    return resolved


def _load_data():
    if not os.path.exists(DATA_FILE):
        return {"manual": [], "opens": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"manual": [], "opens": {}}
        data.setdefault("manual", [])
        data.setdefault("opens", {})
        return data
    except Exception:
        return {"manual": [], "opens": {}}


def _save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
