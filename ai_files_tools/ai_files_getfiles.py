
import os
import json
import datetime
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from ai_files_tools.ai_files_read import resolve_target_path, build_item_info_from_path

DATA_FILE = os.path.join(os.path.dirname(__file__), "common_files.json")


def add_common_file(path):
    normalized = _normalize_path(path)
    if not normalized:
        return {"success": False, "reason": "path_invalid_or_not_found", "message": "路径无效或文件不存在"}
    data = _load_data()
    manual = set(data.get("manual", []))
    manual.add(normalized)
    data["manual"] = sorted(manual)
    _save_data(data)
    return {"success": True, "path": normalized}


def add_common_files_batch(paths_list):
    """
    批量添加常用文件。
    
    Args:
        paths_list (list): 文件路径列表。
    
    Returns:
        list: 每个操作的结果列表。
    """
    results = []
    if not isinstance(paths_list, list):
        return [{"success": False, "reason": "invalid_input", "message": "输入必须是列表"}]

    for path in paths_list:
        result = add_common_file(path)
        result["input_path"] = path
        results.append(result)
    return results


def record_open(path):
    normalized = _normalize_path(path)
    if not normalized:
        return {"success": False, "reason": "path_invalid_or_not_found", "message": "路径无效或文件不存在"}
    data = _load_data()
    opens = data.get("opens", {})
    today = datetime.date.today().strftime("%Y-%m-%d")
    day_set = set(opens.get(today, []))
    day_set.add(normalized)
    opens[today] = sorted(day_set)
    opens = _trim_open_records(opens)
    data["opens"] = opens
    _save_data(data)
    return {"success": True, "path": normalized}


def record_open_batch(paths_list):
    """
    批量记录文件打开。
    
    Args:
        paths_list (list): 文件路径列表。
    
    Returns:
        list: 每个操作的结果列表。
    """
    results = []
    if not isinstance(paths_list, list):
        return [{"success": False, "reason": "invalid_input", "message": "输入必须是列表"}]

    for path in paths_list:
        result = record_open(path)
        result["input_path"] = path
        results.append(result)
    return results


def get_common_files():
    data = _load_data()
    manual = set(data.get("manual", []))
    auto = _get_auto_common_paths(data.get("opens", {}))
    combined = list(manual.union(auto))
    items = []
    for path in combined:
        info = build_item_info_from_path(path)
        if info:
            items.append(info)
    items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    return {"items": items}


def get_common_file_paths():
    data = _load_data()
    manual = set(data.get("manual", []))
    auto = _get_auto_common_paths(data.get("opens", {}))
    return sorted(manual.union(auto))


def _normalize_path(path):
    """
    规范化路径：支持直接路径、快捷方式目标解析。
    """
    # 基础输入校验
    if not path:
        return None
    
    # 解析快捷方式或路径
    resolved = resolve_target_path(path)
    if not resolved:
        # 如果解析失败，尝试直接作为绝对路径
        raw_path = path.strip().strip("\"")
        resolved = os.path.abspath(os.path.normpath(raw_path))

    # 添加时必须是现存路径
    if not os.path.exists(resolved):
        return None

    return resolved


def _get_auto_common_paths(opens):
    dates = _get_recent_dates(3)
    sets = []
    for date_str in dates:
        day_items = opens.get(date_str, [])
        sets.append(set(day_items))
    if not sets:
        return set()
    common = sets[0]
    for day_set in sets[1:]:
        common = common.intersection(day_set)
    return common


def _get_recent_dates(days):
    today = datetime.date.today()
    return [(today - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]


def _trim_open_records(opens):
    dates = set(_get_recent_dates(10))
    return {date: items for date, items in opens.items() if date in dates}


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
