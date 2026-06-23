import json
import os
from datetime import datetime

# 路径配置
# 假设此脚本位于 list/ai_web_tools/
# 数据位于 list/ai_konwledge/web_konwledge/konwledge.json
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "ai_konwledge", "web_konwledge", "konwledge.json")

# 缓存索引，提升检索完整性与性能
_CACHE = {
    "mtime": None,
    "indexed_records": []
}

def load_knowledge():
    """读取知识库文件"""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except Exception as e:
        print(f"读取知识库失败: {e}")
        return []


def _parse_time(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _get_domain(url: str) -> str:
    if not url:
        return ""
    if "://" in url:
        return url.split("://", 1)[1].split("/", 1)[0]
    return url.split("/", 1)[0]


def _build_indexed_records(records):
    """
    构建索引化记录，预计算时间与域名字段。
    """
    indexed = []
    for record in records:
        parsed_time = _parse_time(record.get("start_time", ""))
        url = record.get("url", "") or ""
        indexed.append({
            "record": record,
            "time": parsed_time,
            "date": parsed_time.strftime("%Y-%m-%d") if parsed_time else "",
            "title_lower": (record.get("title", "") or "").lower(),
            "url_lower": url.lower(),
            "domain_lower": _get_domain(url).lower(),
            "browser_lower": (record.get("browser_type", "") or "").lower(),
            "duration": float(record.get("duration", 0) or 0),
            "front_duration": float(record.get("front_duration", 0) or 0),
            "background_duration": float(record.get("background_duration", 0) or 0)
        })
    indexed.sort(key=lambda x: x.get("time") or datetime.min, reverse=True)
    return indexed


def _get_indexed_records():
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

def query_web_knowledge(query_type="recent", limit=0, keyword=None, date=None):
    """
    检索网页浏览知识库。
    
    Args:
        query_type (str): 查询类型。
            - "recent": 最近的浏览记录 (默认)
            - "search": 按关键词搜索标题或URL
            - "stats": 统计信息（如时长统计）
        limit (int): 返回记录数量限制，默认为 0 表示不限制。
        keyword (str): 搜索关键词 (search 模式必填)。
        date (str): 日期过滤 (YYYY-MM-DD)，可选。
    
    Returns:
        list or dict: 查询结果数据。
    """
    data = _get_indexed_records()
    
    if not data:
        return {"message": "知识库为空，暂无浏览记录。"}
    
    results = []
    
    if query_type == "recent":
        for item in data:
            if date and item.get("date") != date:
                continue
            results.append(item["record"])
            if limit and limit > 0 and len(results) >= limit:
                break
        return results

    elif query_type == "search":
        if not keyword:
            return {"error": "搜索模式需要提供 keyword 参数"}
        
        keyword_lower = str(keyword).lower()
        for item in data:
            if date and item.get("date") != date:
                continue
            if keyword_lower in item.get("title_lower", "") or keyword_lower in item.get("url_lower", ""):
                results.append(item["record"])
                if limit and limit > 0 and len(results) >= limit:
                    break
        return results
        
    elif query_type == "stats":
        # 统计模式
        total_duration = 0
        total_front_duration = 0
        total_background_duration = 0
        domain_stats = {}
        record_count = 0
        
        for item in data:
            if date and item.get("date") != date:
                continue
            record_count += 1
            front_duration = item.get("front_duration", 0)
            background_duration = item.get("background_duration", 0)
            duration = item.get("duration", 0)
            merged_duration = front_duration + background_duration
            if merged_duration <= 0 and duration > 0:
                merged_duration = duration
                front_duration = duration
                background_duration = 0
            total_duration += merged_duration
            total_front_duration += front_duration
            total_background_duration += background_duration
            
            # 提取域名
            domain = item.get("domain_lower") or "unknown"
            
            if domain != "unknown":
                domain_stats[domain] = domain_stats.get(domain, 0) + merged_duration
        
        # 排序域名统计
        sorted_domains = sorted(domain_stats.items(), key=lambda x: x[1], reverse=True)
        
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
            "top_sites": [{"domain": k, "duration_seconds": round(v, 2)} for k, v in sorted_domains]
        }

    else:
        return {"error": f"未知的查询类型: {query_type}. 支持: recent, search, stats"}

def clear_web_knowledge():
    """清空网页浏览记录知识库"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False)
        return {"message": "知识库已成功清空。"}
    except Exception as e:
        return {"error": f"清空知识库失败: {str(e)}"}

CONFIG_FILE = os.path.join(BASE_DIR, "ai_konwledge", "web_konwledge", "monitor_config.json")

def toggle_web_monitor(enable=True):
    """
    开启或关闭网页监控功能
    
    Args:
        enable (bool): True 为开启，False 为关闭
    """
    try:
        config = {"enabled": enable}
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False)
        status = "开启" if enable else "关闭"
        return {"message": f"网页监控功能已{status}。"}
    except Exception as e:
        return {"error": f"切换监控状态失败: {str(e)}"}
