
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from ai_files_tools.ai_files_read import read_directory_items, resolve_target_path, resolve_desktop_path


def read_path_details(path):
    normalized = _normalize_path(path)
    if not normalized:
        return {"success": False, "reason": "path_invalid_or_not_found", "message": "路径无效或文件不存在"}

    if os.path.isfile(normalized):
        parent_dir = os.path.dirname(normalized)
        parent_items = read_directory_items(parent_dir)
        return {
            "success": True,
            "input_path": path,
            "resolved_path": normalized,
            "parent_dir": parent_dir,
            "parent_items": parent_items,
            "children_dir": None,
            "children_items": []
        }

    if os.path.isdir(normalized):
        parent_dir = os.path.dirname(normalized)
        parent_items = read_directory_items(parent_dir) if parent_dir else []
        children_items = read_directory_items(normalized)
        return {
            "success": True,
            "input_path": path,
            "resolved_path": normalized,
            "parent_dir": parent_dir,
            "parent_items": parent_items,
            "children_dir": normalized,
            "children_items": children_items
        }

    return {"success": False, "reason": "path_not_found"}


def read_paths_details_batch(paths_list):
    """
    批量读取路径详细信息。
    
    Args:
        paths_list (list): 路径列表。
    
    Returns:
        list: 包含每个路径详细信息的列表。
    """
    results = []
    if not isinstance(paths_list, list):
        return [{"success": False, "reason": "invalid_input", "message": "输入必须是列表"}]

    for path in paths_list:
        result = read_path_details(path)
        results.append(result)
    return results


def _normalize_path(path):
    if not path:
        return None
    
    resolved = resolve_target_path(path)
    if not resolved:
        raw_path = path.strip().strip("\"")
        resolved = os.path.abspath(os.path.normpath(raw_path))

    if not os.path.exists(resolved):
        return None
        
    return resolved
