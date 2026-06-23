import os
import sys
import json
from typing import List, Dict, Any

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from ai_soft_tools.ai_soft_open import open_app

DATA_FILE = os.path.join(current_dir, "favorites.json")


def _ensure_dir():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)


def _normalize_path(path: str) -> str:
    if not path:
        return ""
    raw = str(path).strip().strip("\"")
    raw = os.path.expandvars(raw)
    raw = os.path.expanduser(raw)
    if not os.path.isabs(raw):
        raw = os.path.abspath(raw)
    return os.path.normpath(raw)


def load_favorites() -> List[Dict[str, Any]]:
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except Exception:
        return []


def save_favorites(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    _ensure_dir()
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        return {"success": True, "count": len(items)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_favorite_apps(limit: int = 0) -> Dict[str, Any]:
    items = load_favorites()
    if limit and limit > 0:
        items = items[:limit]
    return {"success": True, "items": items}


def add_favorite_app(path: str, title: str = "") -> Dict[str, Any]:
    norm = _normalize_path(path)
    if not norm:
        return {"success": False, "error": "empty_path"}
    if not os.path.exists(norm):
        return {"success": False, "error": "path_not_found", "path": norm}
    items = load_favorites()
    for item in items:
        if item.get("path") == norm:
            if title:
                item["title"] = title
            return save_favorites(items)
    items.insert(0, {"path": norm, "title": title or os.path.basename(norm)})
    return save_favorites(items)


def remove_favorite_app(keyword: str) -> Dict[str, Any]:
    if not keyword:
        return {"success": False, "error": "empty_keyword"}
    items = load_favorites()
    lower_kw = keyword.lower()
    new_items = [i for i in items if lower_kw not in i.get("path", "").lower() and lower_kw not in i.get("title", "").lower()]
    removed = len(items) - len(new_items)
    result = save_favorites(new_items)
    result["removed"] = removed
    return result


def search_favorite_apps(keyword: str, limit: int = 10) -> Dict[str, Any]:
    if not keyword:
        return {"success": True, "items": []}
    items = load_favorites()
    lower_kw = keyword.lower()
    matched = [i for i in items if lower_kw in i.get("path", "").lower() or lower_kw in i.get("title", "").lower()]
    if limit and limit > 0:
        matched = matched[:limit]
    return {"success": True, "items": matched}


def open_favorite_app(keyword: str) -> Dict[str, Any]:
    items = search_favorite_apps(keyword, limit=1).get("items", [])
    if not items:
        return {"success": False, "error": "not_found"}
    return open_app(items[0]["path"])


def open_favorite_apps_batch(keywords: List[str]) -> Dict[str, Any]:
    if not keywords:
        return {"success": False, "error": "empty_list"}
    opened = []
    failed = []
    for kw in keywords:
        result = open_favorite_app(kw)
        if result.get("success"):
            opened.append(kw)
        else:
            failed.append({"keyword": kw, "error": result.get("error", "open_failed")})
    return {"success": True, "opened": opened, "failed": failed}
