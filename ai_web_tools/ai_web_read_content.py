import json
import socket
import ipaddress
from typing import Dict, Any, List, Union
from urllib.parse import urlparse

import requests

try:
    from ai_web_tools.ai_web_read import get_all_browsers_info
except Exception:
    get_all_browsers_info = None

try:
    from ai_konwledge.web_konwledge.web_monitor_sys import get_active_browser_info
except Exception:
    get_active_browser_info = None


def _is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        if not parsed.hostname:
            return False
        host = parsed.hostname.lower()
        if host in ("localhost", "127.0.0.1"):
            return False
        if host.endswith(".local"):
            return False
        ip = socket.gethostbyname(host)
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_reserved:
            return False
        return True
    except Exception:
        return False


def _fetch_text(url: str, max_bytes: int = 200000) -> Dict[str, Any]:
    if not _is_safe_url(url):
        return {"success": False, "error": "unsafe_url"}
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        response = requests.get(url, headers=headers, timeout=10, stream=True)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if "text" not in content_type and "html" not in content_type and "xml" not in content_type:
            return {"success": False, "error": "unsupported_content_type", "content_type": content_type}
        raw = b""
        for chunk in response.iter_content(chunk_size=4096):
            if not chunk:
                continue
            raw += chunk
            if len(raw) >= max_bytes:
                break
        text = raw.decode(response.encoding or "utf-8", errors="ignore")
        return {"success": True, "text": _extract_readable_text(text)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _extract_readable_text(html: str) -> str:
    import re
    html = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    html = re.sub(r"(?is)<style.*?>.*?</style>", " ", html)
    html = re.sub(r"(?is)<noscript.*?>.*?</noscript>", " ", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    html = re.sub(r"\s+", " ", html).strip()
    return html


def read_open_web_content(mode: str = "active",
                          url: str = "",
                          keyword: str = "",
                          max_pages: int = 3,
                          max_chars: int = 4000) -> Dict[str, Any]:
    targets: List[Dict[str, Any]] = []

    if mode == "url":
        if not url:
            return {"success": False, "error": "empty_url"}
        targets = [{"title": "", "url": url}]
    elif mode == "active":
        if get_active_browser_info:
            info = get_active_browser_info()
            if info and info.get("url") and info.get("url") != "Unknown":
                targets = [info]
        if not targets and get_all_browsers_info:
            items = get_all_browsers_info()
            if items and isinstance(items, list):
                for item in items:
                    if item.get("status") == "success" and item.get("url") and item.get("url") != "Unknown":
                        targets = [item]
                        break
    elif mode == "all":
        if get_all_browsers_info:
            items = get_all_browsers_info()
            if isinstance(items, list):
                for item in items:
                    if item.get("status") == "success" and item.get("url") and item.get("url") != "Unknown":
                        targets.append(item)
    else:
        return {"success": False, "error": "invalid_mode"}

    if keyword:
        lowered = keyword.lower()
        targets = [t for t in targets if lowered in (t.get("title") or "").lower() or lowered in (t.get("url") or "").lower()]

    if max_pages and max_pages > 0:
        targets = targets[:max_pages]

    results = []
    for item in targets:
        item_url = item.get("url", "")
        fetch_result = _fetch_text(item_url)
        if fetch_result.get("success"):
            text = fetch_result.get("text", "")
            if max_chars and max_chars > 0:
                text = text[:max_chars]
            results.append({
                "title": item.get("title", ""),
                "url": item_url,
                "content": text
            })
        else:
            results.append({
                "title": item.get("title", ""),
                "url": item_url,
                "error": fetch_result.get("error")
            })

    return {"success": True, "items": results, "count": len(results)}


def read_web_content_background(urls: Union[List[str], str],
                                max_chars: int = 4000,
                                max_pages: int = 3) -> Dict[str, Any]:
    if isinstance(urls, str):
        url_list = [u.strip() for u in urls.split(",") if u and u.strip()]
    else:
        url_list = [str(u).strip() for u in urls if str(u).strip()]

    if not url_list:
        return {"success": False, "error": "empty_urls"}

    if max_pages and max_pages > 0:
        url_list = url_list[:max_pages]

    items = []
    for item_url in url_list:
        fetch_result = _fetch_text(item_url)
        if fetch_result.get("success"):
            text = fetch_result.get("text", "")
            if max_chars and max_chars > 0:
                text = text[:max_chars]
            items.append({
                "url": item_url,
                "content": text
            })
        else:
            items.append({
                "url": item_url,
                "error": fetch_result.get("error")
            })

    return {"success": True, "items": items, "count": len(items)}
