import os
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
KONWLEDGE_FILE = os.path.join(DATA_DIR, "konwledge.json")

# 缓存索引，避免频繁读取与重复解析
_CACHE = {
    "mtime": None,
    "indexed_records": []
}


def _load_history() -> List[Dict[str, Any]]:
    if not os.path.exists(KONWLEDGE_FILE):
        return []
    try:
        with open(KONWLEDGE_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            data = json.loads(content)
            if isinstance(data, list):
                return data
    except Exception:
        return []
    return []


def _build_indexed_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    构建索引化记录，预解析时间与常用字段，便于快速过滤。
    """
    indexed = []
    for record in records:
        parsed_time = _parse_time(record.get("start_time", ""))
        title = record.get("title", "") or ""
        url = record.get("url", "") or ""
        browser = record.get("browser_type", "") or ""
        indexed.append({
            "record": record,
            "time": parsed_time,
            "date": parsed_time.strftime("%Y-%m-%d") if parsed_time else "",
            "title_lower": title.lower(),
            "url_lower": url.lower(),
            "domain_lower": _get_domain(url).lower(),
            "browser_lower": browser.lower(),
            "duration": float(record.get("duration", 0) or 0)
        })
    indexed.sort(key=lambda x: x.get("time") or datetime.min, reverse=True)
    return indexed


def _get_indexed_records() -> List[Dict[str, Any]]:
    """
    获取索引化记录，文件变更时自动重建索引。
    """
    try:
        mtime = os.path.getmtime(KONWLEDGE_FILE) if os.path.exists(KONWLEDGE_FILE) else None
    except Exception:
        mtime = None
    if _CACHE["mtime"] != mtime:
        records = _load_history()
        _CACHE["indexed_records"] = _build_indexed_records(records)
        _CACHE["mtime"] = mtime
    return _CACHE["indexed_records"]


def _parse_time(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            continue
    return None


def _normalize_records(records: List[Dict[str, Any]], sort_order: str = "desc") -> List[Dict[str, Any]]:
    reverse = str(sort_order).lower() != "asc"
    return sorted(records, key=lambda x: _parse_time(x.get("start_time", "")) or datetime.min, reverse=reverse)


def _apply_limit(records: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    if limit and limit > 0:
        return records[:limit]
    return records


def _get_domain(url: str) -> str:
    if not url:
        return ""
    if "://" in url:
        return url.split("://", 1)[1].split("/", 1)[0]
    return url.split("/", 1)[0]


def _match_text(value: str, keyword: str) -> bool:
    if not keyword:
        return True
    return keyword.lower() in (value or "").lower()


def _match_lower(value_lower: str, keyword_lower: str) -> bool:
    """
    针对已小写化文本的快速包含匹配。
    """
    if not keyword_lower:
        return True
    return keyword_lower in (value_lower or "")


def search_web_history_by_keyword(keyword: str, limit: int = 0) -> Dict[str, Any]:
    if not keyword:
        return {"success": True, "items": [], "total": 0}
    keyword_lower = str(keyword).lower()
    indexed = _get_indexed_records()
    matched = [
        item["record"] for item in indexed
        if _match_lower(item.get("title_lower", ""), keyword_lower)
        or _match_lower(item.get("url_lower", ""), keyword_lower)
    ]
    matched = _apply_limit(matched, limit)
    return {"success": True, "items": matched, "total": len(matched)}


def search_web_history_by_title(title_keyword: str, limit: int = 0) -> Dict[str, Any]:
    if not title_keyword:
        return {"success": True, "items": [], "total": 0}
    keyword_lower = str(title_keyword).lower()
    indexed = _get_indexed_records()
    matched = [item["record"] for item in indexed if _match_lower(item.get("title_lower", ""), keyword_lower)]
    matched = _apply_limit(matched, limit)
    return {"success": True, "items": matched, "total": len(matched)}


def search_web_history_by_name(name_keyword: str, limit: int = 0) -> Dict[str, Any]:
    return search_web_history_by_title(name_keyword, limit)


def search_web_history_by_url(url_keyword: str, limit: int = 0) -> Dict[str, Any]:
    if not url_keyword:
        return {"success": True, "items": [], "total": 0}
    keyword_lower = str(url_keyword).lower()
    indexed = _get_indexed_records()
    matched = [item["record"] for item in indexed if _match_lower(item.get("url_lower", ""), keyword_lower)]
    matched = _apply_limit(matched, limit)
    return {"success": True, "items": matched, "total": len(matched)}


def search_web_history_by_domain(domain_keyword: str, limit: int = 0) -> Dict[str, Any]:
    if not domain_keyword:
        return {"success": True, "items": [], "total": 0}
    keyword_lower = str(domain_keyword).lower()
    indexed = _get_indexed_records()
    matched = [item["record"] for item in indexed if _match_lower(item.get("domain_lower", ""), keyword_lower)]
    matched = _apply_limit(matched, limit)
    return {"success": True, "items": matched, "total": len(matched)}


def search_web_history_by_browser(browser_type: str, limit: int = 0) -> Dict[str, Any]:
    if not browser_type:
        return {"success": True, "items": [], "total": 0}
    keyword_lower = str(browser_type).lower()
    indexed = _get_indexed_records()
    matched = [item["record"] for item in indexed if _match_lower(item.get("browser_lower", ""), keyword_lower)]
    matched = _apply_limit(matched, limit)
    return {"success": True, "items": matched, "total": len(matched)}


def search_web_history_by_date(date: str, limit: int = 0) -> Dict[str, Any]:
    if not date:
        return {"success": True, "items": [], "total": 0}
    indexed = _get_indexed_records()
    matched = [item["record"] for item in indexed if item.get("date") == date]
    matched = _apply_limit(matched, limit)
    return {"success": True, "items": matched, "total": len(matched)}


def search_web_history_by_time_range(start_time: str, end_time: str = "", limit: int = 0) -> Dict[str, Any]:
    if not start_time:
        return {"success": True, "items": [], "total": 0}
    start_dt = _parse_time(start_time)
    end_dt = _parse_time(end_time) if end_time else None
    if start_dt and not end_dt and len(start_time) == 10:
        end_dt = start_dt + timedelta(days=1)
    indexed = _get_indexed_records()
    matched = []
    for item in indexed:
        record_time = item.get("time")
        if not record_time:
            continue
        if start_dt and record_time < start_dt:
            continue
        if end_dt and record_time >= end_dt:
            continue
        matched.append(item["record"])
    matched = _apply_limit(matched, limit)
    return {"success": True, "items": matched, "total": len(matched)}


def search_web_history_combined(
    keyword: str = "",
    title_keyword: str = "",
    name_keyword: str = "",
    url_keyword: str = "",
    domain_keyword: str = "",
    browser_type: str = "",
    date: str = "",
    start_time: str = "",
    end_time: str = "",
    min_duration: float = 0,
    max_duration: float = 0,
    limit: int = 0,
    sort_order: str = "desc"
) -> Dict[str, Any]:
    indexed = _get_indexed_records()
    filtered = []
    start_dt = _parse_time(start_time) if start_time else None
    end_dt = _parse_time(end_time) if end_time else None
    if start_dt and not end_dt and len(start_time) == 10:
        end_dt = start_dt + timedelta(days=1)
    keyword_lower = str(keyword).lower() if keyword else ""
    title_lower = str(title_keyword).lower() if title_keyword else ""
    name_lower = str(name_keyword).lower() if name_keyword else ""
    url_lower = str(url_keyword).lower() if url_keyword else ""
    domain_lower = str(domain_keyword).lower() if domain_keyword else ""
    browser_lower = str(browser_type).lower() if browser_type else ""
    for item in indexed:
        record_time = item.get("time")
        duration = float(item.get("duration", 0) or 0)
        if keyword_lower and not (_match_lower(item.get("title_lower", ""), keyword_lower) or _match_lower(item.get("url_lower", ""), keyword_lower)):
            continue
        if title_lower and not _match_lower(item.get("title_lower", ""), title_lower):
            continue
        if name_lower and not _match_lower(item.get("title_lower", ""), name_lower):
            continue
        if url_lower and not _match_lower(item.get("url_lower", ""), url_lower):
            continue
        if domain_lower and not _match_lower(item.get("domain_lower", ""), domain_lower):
            continue
        if browser_lower and not _match_lower(item.get("browser_lower", ""), browser_lower):
            continue
        if date and record_time and record_time.strftime("%Y-%m-%d") != date:
            continue
        if start_dt and (not record_time or record_time < start_dt):
            continue
        if end_dt and (not record_time or record_time >= end_dt):
            continue
        if min_duration and duration < float(min_duration):
            continue
        if max_duration and duration > float(max_duration):
            continue
        filtered.append(item["record"])
    filtered = _normalize_records(filtered, sort_order)
    filtered = _apply_limit(filtered, limit)
    return {"success": True, "items": filtered, "total": len(filtered)}
