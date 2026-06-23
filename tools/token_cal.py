import os
import sys
import json
from datetime import datetime, timedelta

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

STATS_FILE = os.path.join(project_root, "history_data", "token_usage_stats.json")

_sessions = {}
_active_session_id = None


def _default_stats():
    return {
        "v": 1,
        "total": {"n": 0, "i_c": 0, "i_u": 0, "o": 0, "c": 0.0},
        "daily": {},
        "monthly": {},
        "yearly": {}
    }


def _load_stats():
    if not os.path.exists(STATS_FILE):
        return _default_stats()
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _default_stats()
        data.setdefault("total", {"n": 0, "i_c": 0, "i_u": 0, "o": 0, "c": 0.0})
        data.setdefault("daily", {})
        data.setdefault("monthly", {})
        data.setdefault("yearly", {})
        return data
    except Exception:
        return _default_stats()


def _save_stats(data):
    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def _get_date_keys(now=None):
    now = now or datetime.now()
    day_key = now.strftime("%Y-%m-%d")
    month_key = now.strftime("%Y-%m")
    year_key = now.strftime("%Y")
    return day_key, month_key, year_key


def _ensure_bucket(data, bucket_name, key):
    bucket = data.get(bucket_name, {})
    if key not in bucket:
        bucket[key] = {"n": 0, "i_c": 0, "i_u": 0, "o": 0, "c": 0.0}
    data[bucket_name] = bucket
    return bucket[key]


def _get_rates():
    return {
        "input_cached_per_million": 0.2,
        "input_uncached_per_million": 2.0,
        "output_per_million": 3.0
    }


def _calc_cost(input_cached_tokens, input_uncached_tokens, output_tokens):
    rates = _get_rates()
    cost = (
        input_cached_tokens * rates["input_cached_per_million"] +
        input_uncached_tokens * rates["input_uncached_per_million"] +
        output_tokens * rates["output_per_million"]
    ) / 1_000_000
    return round(cost, 8)


def _extract_cached_tokens(usage):
    if not isinstance(usage, dict):
        return 0
    details = usage.get("prompt_tokens_details") or usage.get("prompt_tokens_detail") or {}
    if isinstance(details, dict):
        cached_tokens = details.get("cached_tokens")
        if isinstance(cached_tokens, int):
            return cached_tokens
    cached_tokens = usage.get("prompt_cache_hit_tokens")
    if isinstance(cached_tokens, int):
        return cached_tokens
    cached_tokens = usage.get("cached_tokens")
    if isinstance(cached_tokens, int):
        return cached_tokens
    return 0


def start_session(session_id):
    if not session_id:
        return
    _sessions[session_id] = {"n": 0, "i_c": 0, "i_u": 0, "o": 0, "c": 0.0}


def set_active_session(session_id):
    global _active_session_id
    _active_session_id = session_id


def get_active_session():
    return _active_session_id


def record_usage(usage, session_id=None):
    if not isinstance(usage, dict):
        return {"success": False, "reason": "usage_invalid"}
    if session_id is None:
        session_id = _active_session_id
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    cached_tokens = int(_extract_cached_tokens(usage))
    if cached_tokens > prompt_tokens:
        cached_tokens = prompt_tokens
    input_uncached = max(prompt_tokens - cached_tokens, 0)
    output_tokens = max(completion_tokens, 0)
    cost = _calc_cost(cached_tokens, input_uncached, output_tokens)

    data = _load_stats()
    day_key, month_key, year_key = _get_date_keys()
    total = data.get("total", {"n": 0, "i_c": 0, "i_u": 0, "o": 0, "c": 0.0})
    total["n"] += 1
    total["i_c"] += cached_tokens
    total["i_u"] += input_uncached
    total["o"] += output_tokens
    total["c"] = round(total.get("c", 0.0) + cost, 8)
    data["total"] = total

    day_bucket = _ensure_bucket(data, "daily", day_key)
    day_bucket["n"] += 1
    day_bucket["i_c"] += cached_tokens
    day_bucket["i_u"] += input_uncached
    day_bucket["o"] += output_tokens
    day_bucket["c"] = round(day_bucket.get("c", 0.0) + cost, 8)

    month_bucket = _ensure_bucket(data, "monthly", month_key)
    month_bucket["n"] += 1
    month_bucket["i_c"] += cached_tokens
    month_bucket["i_u"] += input_uncached
    month_bucket["o"] += output_tokens
    month_bucket["c"] = round(month_bucket.get("c", 0.0) + cost, 8)

    year_bucket = _ensure_bucket(data, "yearly", year_key)
    year_bucket["n"] += 1
    year_bucket["i_c"] += cached_tokens
    year_bucket["i_u"] += input_uncached
    year_bucket["o"] += output_tokens
    year_bucket["c"] = round(year_bucket.get("c", 0.0) + cost, 8)

    _save_stats(data)

    if session_id and session_id in _sessions:
        session_bucket = _sessions[session_id]
        session_bucket["n"] += 1
        session_bucket["i_c"] += cached_tokens
        session_bucket["i_u"] += input_uncached
        session_bucket["o"] += output_tokens
        session_bucket["c"] = round(session_bucket.get("c", 0.0) + cost, 8)

    return {
        "success": True,
        "input_cached": cached_tokens,
        "input_uncached": input_uncached,
        "output": output_tokens,
        "cost": cost
    }


def get_total_summary():
    data = _load_stats()
    total = data.get("total", {"n": 0, "i_c": 0, "i_u": 0, "o": 0, "c": 0.0})
    total_tokens = int(total.get("i_c", 0) + total.get("i_u", 0) + total.get("o", 0))
    return {
        "calls": int(total.get("n", 0)),
        "input_cached": int(total.get("i_c", 0)),
        "input_uncached": int(total.get("i_u", 0)),
        "output": int(total.get("o", 0)),
        "tokens": total_tokens,
        "cost": float(total.get("c", 0.0))
    }


def get_session_summary(session_id):
    session = _sessions.get(session_id) or {"n": 0, "i_c": 0, "i_u": 0, "o": 0, "c": 0.0}
    total_tokens = int(session.get("i_c", 0) + session.get("i_u", 0) + session.get("o", 0))
    return {
        "calls": int(session.get("n", 0)),
        "input_cached": int(session.get("i_c", 0)),
        "input_uncached": int(session.get("i_u", 0)),
        "output": int(session.get("o", 0)),
        "tokens": total_tokens,
        "cost": float(session.get("c", 0.0))
    }


def get_compact_memory_summary():
    data = _load_stats()
    total = data.get("total", {})
    day_key, month_key, year_key = _get_date_keys()
    day_bucket = data.get("daily", {}).get(day_key, {})
    month_bucket = data.get("monthly", {}).get(month_key, {})
    year_bucket = data.get("yearly", {}).get(year_key, {})

    def _sum_tokens(bucket):
        return int(bucket.get("i_c", 0) + bucket.get("i_u", 0) + bucket.get("o", 0))

    total_tokens = _sum_tokens(total)
    day_tokens = _sum_tokens(day_bucket)
    month_tokens = _sum_tokens(month_bucket)
    year_tokens = _sum_tokens(year_bucket)
    return (
        f"[Token统计] 总:{total_tokens} 消费:{total.get('c', 0.0)}元 | "
        f"今日:{day_tokens}/{day_bucket.get('c', 0.0)}元 | "
        f"本月:{month_tokens}/{month_bucket.get('c', 0.0)}元 | "
        f"本年:{year_tokens}/{year_bucket.get('c', 0.0)}元"
    )


def query_usage(date=None, start_date=None, end_date=None, period="day"):
    data = _load_stats()
    if period == "total":
        total = data.get("total", {})
        return _normalize_bucket(total)

    if period in ("day", "month", "year") and date:
        key = _normalize_period_key(date, period)
        bucket = data.get(_period_bucket_name(period), {}).get(key, {})
        return _normalize_bucket(bucket)

    if period == "range" and start_date and end_date:
        return _sum_range(data, start_date, end_date)

    return {"success": False, "reason": "invalid_params"}


def _period_bucket_name(period):
    if period == "month":
        return "monthly"
    if period == "year":
        return "yearly"
    return "daily"


def _normalize_period_key(date_str, period):
    date_str = str(date_str).strip()
    if period == "month":
        return date_str[:7]
    if period == "year":
        return date_str[:4]
    return date_str[:10]


def _normalize_bucket(bucket):
    total_tokens = int(bucket.get("i_c", 0) + bucket.get("i_u", 0) + bucket.get("o", 0))
    return {
        "success": True,
        "calls": int(bucket.get("n", 0)),
        "input_cached": int(bucket.get("i_c", 0)),
        "input_uncached": int(bucket.get("i_u", 0)),
        "output": int(bucket.get("o", 0)),
        "tokens": total_tokens,
        "cost": float(bucket.get("c", 0.0))
    }


def _sum_range(data, start_date, end_date):
    daily = data.get("daily", {})
    start_dt = datetime.strptime(str(start_date)[:10], "%Y-%m-%d")
    end_dt = datetime.strptime(str(end_date)[:10], "%Y-%m-%d")
    if end_dt < start_dt:
        start_dt, end_dt = end_dt, start_dt
    current = start_dt
    bucket = {"n": 0, "i_c": 0, "i_u": 0, "o": 0, "c": 0.0}
    while current <= end_dt:
        key = current.strftime("%Y-%m-%d")
        day_data = daily.get(key, {})
        bucket["n"] += int(day_data.get("n", 0))
        bucket["i_c"] += int(day_data.get("i_c", 0))
        bucket["i_u"] += int(day_data.get("i_u", 0))
        bucket["o"] += int(day_data.get("o", 0))
        bucket["c"] = round(bucket.get("c", 0.0) + float(day_data.get("c", 0.0)), 8)
        current = current + timedelta(days=1)
    return _normalize_bucket(bucket)
