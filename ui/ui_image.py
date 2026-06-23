import os
import base64
from typing import Dict, Any, Optional, Tuple, List

try:
    from PyQt5.QtWidgets import QTextEdit
    from PyQt5.QtGui import QTextCursor, QImage
except Exception:
    QTextEdit = None
    QTextCursor = None
    QImage = None

try:
    from ai_tools import ai_screen
except Exception:
    ai_screen = None


def _list_capture_paths(limit: int = 50) -> List[str]:
    if not ai_screen:
        return []
    result = ai_screen.list_screen_captures(limit=limit)
    if not isinstance(result, dict) or not result.get("success"):
        return []
    items = result.get("items", [])
    return items if isinstance(items, list) else []


def _pick_latest_path(paths: List[str], since_ts: Optional[float]) -> str:
    latest_path = ""
    latest_mtime = 0.0
    for path in paths:
        try:
            mtime = os.path.getmtime(path)
        except Exception:
            continue
        if since_ts is not None and mtime < since_ts:
            continue
        if mtime >= latest_mtime:
            latest_mtime = mtime
            latest_path = path
    return latest_path


def _read_image_base64(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None


def _read_image_size(path: str) -> Optional[Tuple[int, int]]:
    if QImage is None:
        return None
    try:
        image = QImage(path)
        if image.isNull():
            return None
        return image.width(), image.height()
    except Exception:
        return None


def _scale_size(size: Optional[Tuple[int, int]], max_width: int = 600) -> Optional[Tuple[int, int]]:
    if not size:
        return None
    width, height = size
    if width <= 0 or height <= 0:
        return None
    if width <= max_width:
        return width, height
    ratio = max_width / float(width)
    return int(width * ratio), int(height * ratio)


def _build_image_html(base64_data: str, size: Optional[Tuple[int, int]]) -> str:
    if size:
        width, height = size
        return f'<img src="data:image/png;base64,{base64_data}" width="{width}" height="{height}"/>'
    return f'<img src="data:image/png;base64,{base64_data}"/>'


def build_latest_capture_payload(since_ts: Optional[float] = None, max_width: int = 600) -> Dict[str, Any]:
    if not ai_screen:
        return {"success": False, "error": "screen_module_unavailable"}
    paths = _list_capture_paths(limit=50)
    target_path = _pick_latest_path(paths, since_ts)
    if not target_path or not os.path.exists(target_path):
        return {"success": False, "error": "capture_not_found"}
    base64_data = _read_image_base64(target_path)
    if not base64_data:
        return {"success": False, "error": "read_failed", "path": target_path}
    raw_size = _read_image_size(target_path)
    display_size = _scale_size(raw_size, max_width=max_width)
    return {
        "success": True,
        "path": target_path,
        "base64": base64_data,
        "width": display_size[0] if display_size else None,
        "height": display_size[1] if display_size else None
    }


def append_capture_payload_to_chat(editor: "QTextEdit", payload: Dict[str, Any]) -> Dict[str, Any]:
    if QTextEdit is None or not isinstance(editor, QTextEdit):
        return {"success": False, "error": "editor_unavailable"}
    if not isinstance(payload, dict) or not payload.get("success"):
        return {"success": False, "error": "payload_invalid"}
    base64_data = payload.get("base64")
    if not base64_data:
        return {"success": False, "error": "payload_missing_base64"}
    size = None
    width = payload.get("width")
    height = payload.get("height")
    if isinstance(width, int) and isinstance(height, int):
        size = (width, height)
    html = _build_image_html(base64_data, size)
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    if editor.toPlainText().strip():
        cursor.insertHtml("<br/>")
    cursor.insertHtml(html)
    cursor.insertHtml("<br/>")
    editor.setTextCursor(cursor)
    return {"success": True, "path": payload.get("path", "")}


def clear_screen_captures() -> Dict[str, Any]:
    if not ai_screen:
        return {"success": False, "error": "screen_module_unavailable"}
    return ai_screen.clear_screen_captures()


def append_latest_capture_to_chat(editor: "QTextEdit", since_ts: Optional[float] = None, auto_clear: bool = True) -> Dict[str, Any]:
    payload = build_latest_capture_payload(since_ts=since_ts)
    result = append_capture_payload_to_chat(editor, payload)
    if auto_clear and payload.get("success"):
        clear_screen_captures()
    return result
