import os
import json
from datetime import datetime
from typing import List, Dict, Any

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
KONWLEDGE_FILE = os.path.join(DATA_DIR, "konwledge.json")
FAVORITES_FILE = os.path.join(DATA_DIR, "favorites.json")


def _load_json_list(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            data = json.loads(content)
            if isinstance(data, list):
                return data
    except Exception:
        return []
    return []


def _parse_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def read_soft_info(limit: int = 0, date: str = "", include_favorites: bool = True) -> Dict[str, Any]:
    records = _load_json_list(KONWLEDGE_FILE)
    if date:
        filtered = []
        for item in records:
            start_time = _parse_time(item.get("start_time", ""))
            if start_time and start_time.strftime("%Y-%m-%d") == date:
                filtered.append(item)
        records = filtered
    records.sort(key=lambda x: _parse_time(x.get("start_time", "")) or datetime.min, reverse=True)
    if limit and limit > 0:
        records = records[:limit]
    favorites = _load_json_list(FAVORITES_FILE) if include_favorites else []
    return {
        "success": True,
        "records": records,
        "favorites": favorites,
        "record_count": len(records),
        "favorite_count": len(favorites)
    }
