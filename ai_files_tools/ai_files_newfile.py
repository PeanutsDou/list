
import os
import sys

# 确保能导入当前目录下的模块
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from ai_files_tools.ai_files_read import resolve_desktop_path, resolve_target_path

def create_folder(folder_name, parent_path=None):
    """
    在指定路径下新建文件夹。
    
    Args:
        folder_name (str): 新文件夹的名称。
        parent_path (str, optional): 父级目录路径。如果未提供，默认在桌面创建。
    
    Returns:
        dict: 包含操作结果的信息。
    """
    if not folder_name:
        return {"success": False, "reason": "folder_name_empty", "message": "文件夹名称不能为空"}

    # 确定父目录
    if parent_path:
        target_parent = resolve_target_path(parent_path)
    else:
        target_parent = resolve_desktop_path()

    if not target_parent:
         return {"success": False, "reason": "parent_path_invalid", "message": f"无效的父目录: {parent_path or 'Desktop'}"}

    if not os.path.exists(target_parent):
        # 尝试创建父目录（如果是绝对路径且用户意图明确，也许应该允许？但通常 create_folder 只是单层。
        # 如果 parent_path 是不存在的绝对路径，这里报错是合理的）
        return {"success": False, "reason": "parent_path_not_found", "message": f"父目录不存在: {target_parent}"}
    
    if not os.path.isdir(target_parent):
        return {"success": False, "reason": "parent_path_not_dir", "message": f"父路径不是目录: {target_parent}"}

    # 构建完整路径
    full_path = os.path.join(target_parent, folder_name)
    
    # 检查是否存在
    if os.path.exists(full_path):
        return {"success": False, "reason": "already_exists", "path": full_path, "message": "目标路径已存在"}

    try:
        os.makedirs(full_path)
        return {"success": True, "path": full_path, "message": "文件夹创建成功"}
    except Exception as e:
        return {"success": False, "reason": "creation_failed", "error": str(e), "message": f"创建失败: {str(e)}"}

def create_folders_batch(folders_list):
    """
    批量新建文件夹。
    
    Args:
        folders_list (list): 包含文件夹信息的列表，每项为字典 {"name": "...", "path": "..."}。
                             "path" 可选，默认为桌面。
    
    Returns:
        list: 每个操作的结果列表。
    """
    results = []
    if not isinstance(folders_list, list):
        return {"success": False, "reason": "invalid_input", "message": "输入必须是列表"}

    for item in folders_list:
        if not isinstance(item, dict):
            results.append({"success": False, "reason": "invalid_item", "item": item, "message": "列表项必须是字典"})
            continue
            
        name = item.get("name")
        path = item.get("path")
        
        result = create_folder(name, path)
        # 添加原始请求信息以便对应
        result["request"] = item
        results.append(result)
        
    return results
