import os
from typing import Dict, Any


def _normalize_path(path: str) -> str:
    if not path:
        return ""
    raw = str(path).strip().strip("\"")
    raw = os.path.expandvars(raw)
    raw = os.path.expanduser(raw)
    if not os.path.isabs(raw):
        raw = os.path.abspath(raw)
    return os.path.normpath(raw)


def open_app(path: str) -> Dict[str, Any]:
    normalized = _normalize_path(path)
    if not normalized:
        return {"success": False, "error": "empty_path"}
    if not os.path.exists(normalized):
        return {"success": False, "error": "path_not_found", "path": normalized}
    try:
        os.startfile(normalized)
        return {"success": True, "path": normalized}
    except Exception as e:
        return {"success": False, "error": str(e), "path": normalized}
