
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from ai_files_tools.ai_files_read import resolve_desktop_path, resolve_target_path, validate_path_security


def create_markdown_file(file_name, content=None, parent_path=None):
    if not file_name:
        return {"success": False, "reason": "file_name_empty", "message": "文件名不能为空"}
    target_parent = _resolve_parent_path(parent_path)
    if not target_parent:
        return {"success": False, "reason": "parent_path_invalid", "message": "无法定位父目录"}
    safe_name = _ensure_extension(str(file_name).strip(), ".md")
    full_path = os.path.join(target_parent, safe_name)
    
    if os.path.exists(full_path):
        return {"success": False, "reason": "already_exists", "path": full_path, "message": "目标文件已存在"}
    try:
        text = "" if content is None else str(content)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(text)
        return {"success": True, "path": full_path, "message": "创建成功"}
    except Exception as e:
        return {"success": False, "reason": "create_failed", "error": str(e), "message": f"创建失败: {str(e)}"}


def update_markdown_content(file_path, content):
    """
    更新 Markdown 文档内容。
    
    功能说明:
    将指定内容覆盖写入到 Markdown 文件中。如果文件不存在或路径无效，则返回失败。
    
    参数:
    file_path (str): Markdown 文件的路径。
    content (str): 要写入的新内容。
    """
    normalized = _normalize_existing_path(file_path, ".md")
    if not normalized:
        return {"success": False, "reason": "path_invalid_or_not_found", "message": "路径无效或文件不存在"}
    try:
        text = "" if content is None else str(content)
        with open(normalized, "w", encoding="utf-8") as f:
            f.write(text)
        return {"success": True, "path": normalized, "message": "内容已更新"}
    except Exception as e:
        return {"success": False, "reason": "update_failed", "error": str(e), "message": f"更新失败: {str(e)}"}


def append_markdown_content(file_path, content):
    """
    追加 Markdown 文档内容。
    
    功能说明:
    将指定内容追加到 Markdown 文件的末尾。
    
    参数:
    file_path (str): Markdown 文件的路径。
    content (str): 要追加的内容。
    """
    normalized = _normalize_existing_path(file_path, ".md")
    if not normalized:
        return {"success": False, "reason": "path_invalid_or_not_found", "message": "路径无效或文件不存在"}
    if content is None:
        return {"success": False, "reason": "content_empty", "message": "追加内容不能为空"}
    try:
        with open(normalized, "a", encoding="utf-8") as f:
            f.write(str(content))
        return {"success": True, "path": normalized, "message": "内容已追加"}
    except Exception as e:
        return {"success": False, "reason": "append_failed", "error": str(e), "message": f"追加失败: {str(e)}"}


def read_markdown_file(file_path):
    """
    读取 Markdown 文档内容。
    
    功能说明:
    读取指定 Markdown 文件的全部内容。
    
    参数:
    file_path (str): Markdown 文件的路径。
    """
    normalized = _normalize_existing_path(file_path, ".md")
    if not normalized:
        return {"success": False, "reason": "path_invalid_or_not_found", "message": "路径无效或文件不存在"}
    try:
        with open(normalized, "r", encoding="utf-8") as f:
            content = f.read()
        return {"success": True, "path": normalized, "content": content}
    except Exception as e:
        return {"success": False, "reason": "read_failed", "error": str(e), "message": f"读取失败: {str(e)}"}


def remove_markdown_content(file_path, content):
    """
    移除 Markdown 文档中的指定内容。
    
    功能说明:
    从 Markdown 文件中查找并删除指定的字符串内容。
    
    参数:
    file_path (str): Markdown 文件的路径。
    content (str): 要删除的内容字符串。
    """
    normalized = _normalize_existing_path(file_path, ".md")
    if not normalized:
        return {"success": False, "reason": "path_invalid_or_not_found", "message": "路径无效或文件不存在"}
    if not content:
        return {"success": False, "reason": "content_empty", "message": "要删除的内容不能为空"}
    try:
        with open(normalized, "r", encoding="utf-8") as f:
            original = f.read()
        updated = original.replace(str(content), "")
        if updated == original:
            return {"success": False, "reason": "content_not_found", "path": normalized, "message": "未找到要删除的内容"}
        with open(normalized, "w", encoding="utf-8") as f:
            f.write(updated)
        return {"success": True, "path": normalized, "message": "内容已删除"}
    except Exception as e:
        return {"success": False, "reason": "remove_failed", "error": str(e), "message": f"删除失败: {str(e)}"}


def delete_markdown_file(file_path):
    """
    删除 Markdown 文档。
    
    功能说明:
    删除指定的 Markdown 文件。
    
    参数:
    file_path (str): Markdown 文件的路径。
    """
    normalized = _normalize_existing_path(file_path, ".md")
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
