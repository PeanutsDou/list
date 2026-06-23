import os
import base64
from datetime import datetime
from typing import Dict, Any, List, Tuple

from ai_files_tools.ai_files_read import resolve_desktop_path

try:
    from PIL import ImageGrab, Image
except Exception:
    ImageGrab = None
    Image = None

try:
    from PyQt5.QtGui import QGuiApplication, QImage
except Exception:
    QGuiApplication = None
    QImage = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "core", "core_data", "screen_captures")


def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)


def _normalize_region(region) -> Tuple[int, int, int, int] | None:
    if not region:
        return None
    if isinstance(region, (list, tuple)) and len(region) == 4:
        try:
            left, top, right, bottom = [int(x) for x in region]
            if right > left and bottom > top:
                return left, top, right, bottom
        except Exception:
            return None
    return None


def _build_capture_path(path: str = "") -> str:
    _ensure_dirs()
    if path:
        raw = str(path).strip().strip("\"")
        if os.path.isabs(raw):
            return os.path.normpath(raw)
        return os.path.normpath(os.path.join(DATA_DIR, raw))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"screen_{timestamp}.png"
    return os.path.join(DATA_DIR, name)


def _capture_with_pil(path: str, region: Tuple[int, int, int, int] | None) -> Dict[str, Any]:
    if ImageGrab is None:
        return {"success": False, "error": "pillow_unavailable"}
    try:
        image = ImageGrab.grab(bbox=region) if region else ImageGrab.grab()
        _ensure_dirs()
        image.save(path, "PNG")
        return {"success": True, "path": path, "width": image.width, "height": image.height}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _capture_with_pyqt(path: str, region: Tuple[int, int, int, int] | None) -> Dict[str, Any]:
    if QGuiApplication is None:
        return {"success": False, "error": "pyqt_unavailable"}
    try:
        app = QGuiApplication.instance()
        if app is None:
            app = QGuiApplication([])
        screen = app.primaryScreen()
        if screen is None:
            return {"success": False, "error": "screen_not_found"}
        if region:
            left, top, right, bottom = region
            width = max(1, right - left)
            height = max(1, bottom - top)
            pixmap = screen.grabWindow(0, left, top, width, height)
        else:
            pixmap = screen.grabWindow(0)
        _ensure_dirs()
        ok = pixmap.save(path, "PNG")
        if not ok:
            return {"success": False, "error": "save_failed"}
        return {"success": True, "path": path, "width": pixmap.width(), "height": pixmap.height()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def capture_screen(path: str = "", region: List[int] | Tuple[int, int, int, int] | None = None) -> Dict[str, Any]:
    target_path = _build_capture_path(path)
    normalized_region = _normalize_region(region)
    result = _capture_with_pil(target_path, normalized_region)
    if result.get("success"):
        return result
    return _capture_with_pyqt(target_path, normalized_region)


def capture_screen_base64(path: str = "", region: List[int] | Tuple[int, int, int, int] | None = None, max_chars: int = 0) -> Dict[str, Any]:
    result = capture_screen(path=path, region=region)
    if not result.get("success"):
        return result
    file_path = result.get("path")
    if not file_path or not os.path.exists(file_path):
        return {"success": False, "error": "capture_not_found"}
    try:
        with open(file_path, "rb") as f:
            raw = f.read()
        encoded = base64.b64encode(raw).decode("utf-8")
        if max_chars and max_chars > 0:
            encoded = encoded[:max_chars]
        result.update({"base64": encoded, "base64_truncated": bool(max_chars and max_chars > 0)})
        return result
    except Exception as e:
        return {"success": False, "error": str(e), "path": file_path}


def save_screen_capture(target_dir: str = "", file_name: str = "", name_prefix: str = "screen", region: List[int] | Tuple[int, int, int, int] | None = None) -> Dict[str, Any]:
    desktop_dir = resolve_desktop_path()
    base_dir = ""
    if target_dir:
        raw_dir = str(target_dir).strip().strip("\"")
        if os.path.isabs(raw_dir):
            base_dir = os.path.normpath(raw_dir)
        else:
            base_dir = os.path.normpath(os.path.join(desktop_dir or os.getcwd(), raw_dir))
    else:
        base_dir = os.path.normpath(desktop_dir or os.getcwd())
    try:
        os.makedirs(base_dir, exist_ok=True)
    except Exception as e:
        return {"success": False, "error": str(e), "path": base_dir}
    raw_name = str(file_name).strip().strip("\"") if file_name is not None else ""
    final_name = raw_name
    if not final_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = str(name_prefix).strip() if name_prefix else "screen"
        final_name = f"{prefix}_{timestamp}.png"
    else:
        name_root, ext = os.path.splitext(final_name)
        if not ext:
            final_name = f"{final_name}.png"
    final_path = os.path.normpath(os.path.join(base_dir, os.path.basename(final_name)))
    result = capture_screen(path=final_path, region=region)
    if result.get("success"):
        result.update({"directory": base_dir, "file_name": os.path.basename(final_name)})
    return result


def list_screen_captures(limit: int = 20) -> Dict[str, Any]:
    _ensure_dirs()
    try:
        files = []
        for name in os.listdir(DATA_DIR):
            path = os.path.join(DATA_DIR, name)
            if os.path.isfile(path) and name.lower().endswith(".png"):
                files.append(path)
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        if limit and limit > 0:
            files = files[:limit]
        return {"success": True, "items": files, "count": len(files)}
    except Exception as e:
        return {"success": False, "error": str(e), "items": []}


def get_latest_screen_capture_path() -> Dict[str, Any]:
    data = list_screen_captures(limit=1)
    if not data.get("success"):
        return data
    items = data.get("items", [])
    return {"success": True, "path": items[0] if items else ""}


def _get_image_size(path: str) -> Tuple[int, int] | None:
    if Image is not None:
        try:
            with Image.open(path) as img:
                return img.width, img.height
        except Exception:
            return None
    if QImage is not None:
        try:
            image = QImage(path)
            if image.isNull():
                return None
            return image.width(), image.height()
        except Exception:
            return None
    return None


def read_screen_capture_info(path: str = "") -> Dict[str, Any]:
    target_path = ""
    if path:
        target_path = _build_capture_path(path)
    else:
        latest = get_latest_screen_capture_path()
        if not latest.get("success"):
            return latest
        target_path = latest.get("path", "")
    if not target_path or not os.path.exists(target_path):
        return {"success": False, "error": "path_not_found", "path": target_path}
    size = _get_image_size(target_path)
    try:
        stat = os.stat(target_path)
        return {
            "success": True,
            "path": target_path,
            "size_bytes": stat.st_size,
            "modified_time": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "width": size[0] if size else None,
            "height": size[1] if size else None
        }
    except Exception as e:
        return {"success": False, "error": str(e), "path": target_path}


def clear_screen_captures() -> Dict[str, Any]:
    _ensure_dirs()
    try:
        removed = 0
        for name in os.listdir(DATA_DIR):
            path = os.path.join(DATA_DIR, name)
            if os.path.isfile(path) and name.lower().endswith(".png"):
                os.remove(path)
                removed += 1
        return {"success": True, "removed": removed}
    except Exception as e:
        return {"success": False, "error": str(e)}
