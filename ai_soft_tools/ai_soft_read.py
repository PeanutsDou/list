from typing import Dict, Any, List

try:
    from ai_konwledge.soft_konwledge.soft_monitor_sys import get_all_app_windows_info
except Exception:
    get_all_app_windows_info = None


def get_all_apps_info() -> Dict[str, Any]:
    if get_all_app_windows_info is None:
        return {"success": False, "error": "monitor_unavailable", "items": []}
    try:
        items: List[Dict[str, Any]] = get_all_app_windows_info()
        return {"success": True, "items": items, "count": len(items)}
    except Exception as e:
        return {"success": False, "error": str(e), "items": []}
