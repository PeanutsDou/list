
"""
文件搜索工具：支持指定目录或全盘搜索。
"""

import os
import sys
from typing import Dict, List

# 确保能导入当前目录下的模块
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from ai_files_tools.ai_files_read import resolve_desktop_path, read_directory_items, build_item_info_from_path, get_drives, resolve_target_path

def search_files_by_name(name: str, root_path: str = None, limit: int = 50) -> Dict[str, List[dict]]:
    """
    在指定目录（默认为桌面）及其子目录中按名称搜索文件。
    
    Args:
        name (str): 关键词。
        root_path (str): 搜索根目录。如果为 None，默认搜索桌面。
                         如果要搜索全盘，请多次调用或传入盘符。
        limit (int): 最大返回数量。

    Returns:
        dict: 搜索结果。
    """
    if not name or not str(name).strip():
        return {"success": False, "reason": "name_empty", "message": "名称关键词不能为空", "matched_items": []}

    # 确定搜索根目录
    if root_path:
        # 使用 resolve_target_path 解析输入路径（支持 Desktop 别名等）
        start_dir = resolve_target_path(root_path)
        if not start_dir or not os.path.isdir(start_dir):
             return {"success": False, "reason": "invalid_root_path", "message": f"无效的搜索根目录: {root_path}", "matched_items": []}
    else:
        start_dir = resolve_desktop_path()
        if not start_dir:
            return {"success": False, "reason": "desktop_not_found", "message": "无法定位桌面路径", "matched_items": []}

    keyword = str(name).strip().lower()
    matched_items = []
    
    try:
        # 使用 os.walk 进行递归搜索
        for root, dirs, files in os.walk(start_dir):
            # 优化：跳过系统目录或隐藏目录（可选，视需求而定，这里简单跳过 .git 等）
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            # 检查目录名
            for dirname in dirs:
                if keyword in dirname.lower():
                    info = build_item_info_from_path(os.path.join(root, dirname))
                    if info:
                        matched_items.append(info)
                        if limit > 0 and len(matched_items) >= limit:
                            break
            
            if limit > 0 and len(matched_items) >= limit:
                break
                
            # 检查文件名
            for filename in files:
                if keyword in filename.lower():
                    info = build_item_info_from_path(os.path.join(root, filename))
                    if info:
                        matched_items.append(info)
                        if limit > 0 and len(matched_items) >= limit:
                            break
            
            if limit > 0 and len(matched_items) >= limit:
                break
    except Exception as e:
        return {"success": False, "reason": "search_error", "message": str(e), "matched_items": matched_items}

    return {
        "success": True,
        "query": name,
        "search_root": start_dir,
        "matched_count": len(matched_items),
        "matched_items": matched_items
    }

def list_system_drives():
    """列出系统所有盘符，辅助用户决定搜索范围"""
    drives = get_drives()
    return {
        "success": True,
        "drives": drives,
        "count": len(drives)
    }

# 保留旧接口兼容性，但指向新逻辑
def search_desktop_files_by_name(name: str) -> Dict[str, List[dict]]:
    return search_files_by_name(name, root_path=None)

def search_desktop_files_recursive(name: str, limit: int = 0) -> Dict[str, List[dict]]:
    return search_files_by_name(name, root_path=None, limit=limit)
