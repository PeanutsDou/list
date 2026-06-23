
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from ai_files_tools.ai_files_read import resolve_desktop_path, resolve_target_path


def read_pdf_file(file_path, max_pages=5):
    normalized = _normalize_existing_path(file_path, ".pdf")
    if not normalized:
        return {"success": False, "reason": "path_invalid_or_not_found", "message": "路径无效或文件不存在"}
    try:
        text = _extract_pdf_text(normalized, max_pages)
        return {"success": True, "path": normalized, "content": text}
    except Exception as e:
        return {"success": False, "reason": "read_failed", "error": str(e), "message": f"读取失败: {str(e)}"}


def delete_pdf_file(file_path):
    normalized = _normalize_existing_path(file_path, ".pdf")
    if not normalized:
        return {"success": False, "reason": "path_invalid_or_not_found", "message": "路径无效或文件不存在"}
    try:
        os.remove(normalized)
        return {"success": True, "path": normalized, "message": "删除成功"}
    except Exception as e:
        return {"success": False, "reason": "delete_failed", "error": str(e), "message": f"删除失败: {str(e)}"}


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


def _ensure_extension(name, extension):
    if name.lower().endswith(extension):
        return name
    return f"{name}{extension}"


def _extract_pdf_text(path, max_pages):
    from PyPDF2 import PdfReader
    reader = PdfReader(path)
    texts = []
    total_pages = len(reader.pages)
    limit = min(int(max_pages), total_pages) if max_pages else total_pages
    for index in range(limit):
        page = reader.pages[index]
        texts.append(page.extract_text() or "")
    return "\n".join(texts)
