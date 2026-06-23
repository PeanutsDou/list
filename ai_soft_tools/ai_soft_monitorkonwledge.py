import json
import os
from datetime import datetime
from typing import Dict, Any, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "ai_konwledge", "soft_konwledge", "konwledge.json")
CONFIG_FILE = os.path.join(BASE_DIR, "ai_konwledge", "soft_konwledge", "monitor_config.json")

# 缓存索引，提升检索完整性与性能
_CACHE = {
    "mtime": None,
    "indexed_records": []
}

def load_knowledge() -> List[Dict[str, Any]]:
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            data = json.loads(content)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _build_indexed_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    构建索引化记录，预解析常用字段便于快速过滤。
    """
    indexed = []
    for record in records:
        parsed_time = _parse_time(record.get("start_time", ""))
        title = record.get("title", "") or ""
        app_name = record.get("app_name", "") or ""
        process_name = record.get("process_name", "") or ""
        exe_path = record.get("exe_path", "") or ""
        indexed.append({
            "record": record,
            "time": parsed_time,
            "date": parsed_time.strftime("%Y-%m-%d") if parsed_time else "",
            "title_lower": title.lower(),
            "app_lower": app_name.lower(),
            "process_lower": process_name.lower(),
            "exe_lower": exe_path.lower(),
            "duration": float(record.get("duration", 0) or 0),
            "front_duration": float(record.get("front_duration", 0) or 0),
            "background_duration": float(record.get("background_duration", 0) or 0)
        })
    indexed.sort(key=lambda x: x.get("time") or datetime.min, reverse=True)
    return indexed


def _get_indexed_records() -> List[Dict[str, Any]]:
    """
    获取索引化记录，文件变更时自动重建。
    """
    try:
        mtime = os.path.getmtime(DATA_FILE) if os.path.exists(DATA_FILE) else None
    except Exception:
        mtime = None
    if _CACHE["mtime"] != mtime:
        records = load_knowledge()
        _CACHE["indexed_records"] = _build_indexed_records(records)
        _CACHE["mtime"] = mtime
    return _CACHE["indexed_records"]


def _parse_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _match_text(value: str, keyword: str) -> bool:
    if not keyword:
        return True
    return keyword.lower() in (value or "").lower()


def query_soft_knowledge(query_type: str = "recent", limit: int = 0, keyword: str | None = None, date: str | None = None) -> Dict[str, Any]:
    data = _get_indexed_records()
    if not data:
        return {"message": "知识库为空，暂无软件使用记录。"}
    results: List[Dict[str, Any]] = []
    if query_type == "recent":
        for item in data:
            if date and item.get("date") != date:
                continue
            results.append(item["record"])
            if limit and limit > 0 and len(results) >= limit:
                break
        return results
    if query_type == "search":
        if not keyword:
            return {"error": "搜索模式需要提供 keyword 参数"}
        keyword_lower = str(keyword).lower()
        for item in data:
            if keyword_lower in item.get("title_lower", "") or keyword_lower in item.get("app_lower", "") or keyword_lower in item.get("process_lower", "") or keyword_lower in item.get("exe_lower", ""):
                results.append(item["record"])
                if limit and limit > 0 and len(results) >= limit:
                    break
        return results
    if query_type == "stats":
        record_count = len(data)
        total_duration = 0.0
        total_front_duration = 0.0
        total_background_duration = 0.0
        app_stats: Dict[str, float] = {}
        for item in data:
            duration = float(item.get("duration", 0) or 0)
            front_duration = float(item.get("front_duration", 0) or 0)
            background_duration = float(item.get("background_duration", 0) or 0)
            total_duration += duration
            total_front_duration += front_duration
            total_background_duration += background_duration
            record = item.get("record", {})
            app_name = record.get("app_name") or record.get("process_name") or "unknown"
            if app_name:
                app_stats[app_name] = app_stats.get(app_name, 0) + duration
        sorted_apps = sorted(app_stats.items(), key=lambda x: x[1], reverse=True)
        return {
            "query_date": date if date else "all_time",
            "total_records": record_count,
            "total_duration_seconds": round(total_duration, 2),
            "total_duration_minutes": round(total_duration / 60, 2),
            "total_duration_hours": round(total_duration / 3600, 2),
            "front_duration_seconds": round(total_front_duration, 2),
            "front_duration_minutes": round(total_front_duration / 60, 2),
            "front_duration_hours": round(total_front_duration / 3600, 2),
            "background_duration_seconds": round(total_background_duration, 2),
            "background_duration_minutes": round(total_background_duration / 60, 2),
            "background_duration_hours": round(total_background_duration / 3600, 2),
            "top_apps": [{"name": k, "duration_seconds": round(v, 2)} for k, v in sorted_apps]
        }
    return {"error": f"未知的查询类型: {query_type}. 支持: recent, search, stats"}


def clear_soft_knowledge() -> Dict[str, Any]:
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)
        return {"message": "知识库已成功清空。"}
    except Exception as e:
        return {"error": f"清空知识库失败: {str(e)}"}


def toggle_soft_monitor(enable: bool = True) -> Dict[str, Any]:
    try:
        config = {"enabled": enable}
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False)
        status = "开启" if enable else "关闭"
        return {"message": f"软件监控功能已{status}。"}
    except Exception as e:
        return {"error": f"切换监控状态失败: {str(e)}"}
