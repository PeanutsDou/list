
import os
import sys

# 确保能导入当前目录下的模块
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from ai_files_tools.ai_files_read import resolve_desktop_path, resolve_target_path

def create_py_file(file_name, content=None, parent_path=None):
    """
    新建 Python 脚本文件。
    
    功能说明:
    在指定目录（默认为桌面）创建一个新的 .py 文件。
    
    参数:
    file_name (str): 文件名（如 script.py）。
    content (str, optional): 文件初始代码内容。
    parent_path (str, optional): 父目录路径，不传默认桌面。
    
    返回:
    dict: 包含 success, path, message 等信息。
    """
    if not file_name:
        return {"success": False, "reason": "file_name_empty", "message": "文件名不能为空"}
    target_parent = _resolve_parent_path(parent_path)
    if not target_parent:
        return {"success": False, "reason": "parent_path_invalid", "message": "无法定位父目录"}
    
    safe_name = _ensure_extension(str(file_name).strip(), ".py")
    full_path = os.path.join(target_parent, safe_name)
    
    if os.path.exists(full_path):
        return {"success": False, "reason": "already_exists", "path": full_path, "message": "目标文件已存在"}
    
    try:
        text = "" if content is None else str(content)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(text)
        return {"success": True, "path": full_path, "message": "Python 脚本创建成功"}
    except Exception as e:
        return {"success": False, "reason": "create_failed", "error": str(e), "message": f"创建失败: {str(e)}"}

def read_py_file(file_path):
    """
    读取 Python 脚本内容。
    
    参数:
    file_path (str): .py 文件的路径或名称。
    """
    normalized = _normalize_existing_path(file_path, ".py")
    if not normalized:
        return {"success": False, "reason": "path_invalid_or_not_found", "message": "路径无效或文件不存在"}
    try:
        with open(normalized, "r", encoding="utf-8") as f:
            content = f.read()
        return {"success": True, "path": normalized, "content": content}
    except Exception as e:
        return {"success": False, "reason": "read_failed", "error": str(e), "message": f"读取失败: {str(e)}"}

def update_py_content(file_path, content, mode="replace"):
    """
    更新 Python 脚本内容。
    
    参数:
    file_path (str): .py 文件的路径或名称。
    content (str): 新的代码内容。
    mode (str): 更新模式，'replace' (覆盖) 或 'append' (追加)。
    """
    normalized = _normalize_existing_path(file_path, ".py")
    if not normalized:
        return {"success": False, "reason": "path_invalid_or_not_found", "message": "路径无效或文件不存在"}
    
    mode = str(mode).lower()
    if mode not in ["replace", "append"]:
        return {"success": False, "reason": "invalid_mode", "message": "无效的模式，仅支持 replace 或 append"}
        
    try:
        write_mode = "w" if mode == "replace" else "a"
        text = "" if content is None else str(content)
        
        # 追加模式下，如果是追加新代码，通常建议先换行
        if mode == "append" and text:
            # 简单读取判断是否需要换行
            try:
                with open(normalized, "r", encoding="utf-8") as f:
                    existing = f.read()
                if existing and not existing.endswith("\n"):
                    text = "\n" + text
            except:
                pass

        with open(normalized, write_mode, encoding="utf-8") as f:
            f.write(text)
        return {"success": True, "path": normalized, "message": "内容已更新", "mode": mode}
    except Exception as e:
        return {"success": False, "reason": "update_failed", "error": str(e), "message": f"更新失败: {str(e)}"}

def delete_py_file(file_path):
    """
    删除 Python 脚本文件。
    
    参数:
    file_path (str): .py 文件的路径或名称。
    """
    normalized = _normalize_existing_path(file_path, ".py")
    if not normalized:
        return {"success": False, "reason": "path_invalid_or_not_found", "message": "路径无效或文件不存在"}
    try:
        os.remove(normalized)
        return {"success": True, "path": normalized, "message": "删除成功"}
    except Exception as e:
        return {"success": False, "reason": "delete_failed", "error": str(e), "message": f"删除失败: {str(e)}"}

def _resolve_parent_path(parent_path):
    if parent_path:
        target_parent = resolve_target_path(parent_path)
    else:
        target_parent = resolve_desktop_path()
    if not target_parent or not os.path.exists(target_parent) or not os.path.isdir(target_parent):
        return None
    return os.path.abspath(os.path.normpath(target_parent))

def _ensure_extension(name, extension):
    if name.lower().endswith(extension):
        return name
    return f"{name}{extension}"

def _normalize_existing_path(path, extension):
    if not path:
        return None
    resolved = resolve_target_path(path)
    if not resolved or not os.path.exists(resolved):
        return None
    resolved = os.path.abspath(os.path.normpath(resolved))
    if not resolved.lower().endswith(extension):
        return None
    return resolved
