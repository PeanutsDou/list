
import os
import sys
import shutil

# 确保能导入当前目录下的模块
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from ai_files_tools.ai_files_read import resolve_target_path

def delete_file(path):
    """
    删除指定的文件或文件夹。
    
    Args:
        path (str): 要删除的文件或文件夹路径。
    
    Returns:
        dict: 包含操作结果的信息。
    """
    if not path:
        return {"success": False, "reason": "path_empty", "message": "路径不能为空"}

    # 解析路径
    target_path = resolve_target_path(path)

    # 再次确认存在性
    if not target_path or not os.path.exists(target_path):
        return {"success": False, "reason": "not_found", "path": target_path or path, "message": "文件或文件夹不存在"}

    try:
        if os.path.isfile(target_path) or os.path.islink(target_path):
            os.remove(target_path)
        elif os.path.isdir(target_path):
            shutil.rmtree(target_path)
        else:
            # 可能是特殊的系统文件类型
            os.remove(target_path)
            
        return {"success": True, "path": target_path, "message": "删除成功"}
    except Exception as e:
        return {"success": False, "reason": "delete_failed", "path": target_path, "error": str(e), "message": f"删除失败: {str(e)}"}

def delete_files_batch(paths_list):
    """
    批量删除文件或文件夹。
    
    Args:
        paths_list (list): 文件或文件夹路径列表。
    
    Returns:
        list: 每个操作的结果列表。
    """
    results = []
    if not isinstance(paths_list, list):
        return [{"success": False, "reason": "invalid_input", "message": "输入必须是列表"}]

    for path in paths_list:
        result = delete_file(path)
        result["input_path"] = path
        results.append(result)
        
    return results
