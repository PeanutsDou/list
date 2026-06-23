import os
import sys
import json
from typing import List, Dict, Any

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from ai_web_tools.ai_web_open import open_url

DATA_FILE = os.path.join(current_dir, "favorites.json")


def _ensure_dir():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)


def _normalize_url(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if not url.startswith(("http://", "https://", "file://")):
        url = "https://" + url
    return url


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


def list_favorite_urls(limit: int = 0) -> Dict[str, Any]:
    items = load_favorites()
    if limit and limit > 0:
        items = items[:limit]
    return {"success": True, "items": items}


def add_favorite_url(url: str, title: str = "") -> Dict[str, Any]:
    norm = _normalize_url(url)
    if not norm:
        return {"success": False, "error": "empty_url"}
    items = load_favorites()
    for item in items:
        if item.get("url") == norm:
            if title:
                item["title"] = title
            return save_favorites(items)
    items.insert(0, {"url": norm, "title": title or norm})
    return save_favorites(items)


def remove_favorite_url(keyword: str) -> Dict[str, Any]:
    if not keyword:
        return {"success": False, "error": "empty_keyword"}
    items = load_favorites()
    lower_kw = keyword.lower()
    new_items = [i for i in items if lower_kw not in i.get("url", "").lower() and lower_kw not in i.get("title", "").lower()]
    removed = len(items) - len(new_items)
    result = save_favorites(new_items)
    result["removed"] = removed
    return result


def search_favorite_urls(keyword: str, limit: int = 10) -> Dict[str, Any]:
    if not keyword:
        return {"success": True, "items": []}
    items = load_favorites()
    lower_kw = keyword.lower()
    matched = [i for i in items if lower_kw in i.get("url", "").lower() or lower_kw in i.get("title", "").lower()]
    if limit and limit > 0:
        matched = matched[:limit]
    return {"success": True, "items": matched}


def open_favorite_url(keyword: str) -> Dict[str, Any]:
    items = search_favorite_urls(keyword, limit=1).get("items", [])
    if not items:
        return {"success": False, "error": "not_found"}
    return open_url(items[0]["url"])


def open_favorite_urls_batch(keywords: List[str]) -> Dict[str, Any]:
    if not keywords:
        return {"success": False, "error": "empty_list"}
    opened = []
    failed = []
    for kw in keywords:
        result = open_favorite_url(kw)
        if result.get("status") == "success":
            opened.append(kw)
        else:
            failed.append({"keyword": kw, "error": result.get("error", "open_failed")})
    return {"success": True, "opened": opened, "failed": failed}
