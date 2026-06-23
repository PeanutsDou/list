import os
import json
import base64
import requests
from urllib.parse import urlparse
import sys

# 确保能导入 tools
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from tools.config_loader import get_github_config
except ImportError:
    def get_github_config():
        return {}


def _project_root():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(current_dir)


def resolve_github_token(token=None, token_file=None, token_env="GITHUB_TOKEN"):
    if token:
        return str(token).strip()
    
    # 优先从 config.json 读取
    config = get_github_config()
    config_token = config.get("token")
    if config_token:
        return str(config_token).strip()

    env_value = os.environ.get(token_env)
    if env_value:
        return str(env_value).strip()
    if not token_file:
        token_file = os.path.join(_project_root(), "github token")
    if os.path.exists(token_file):
        try:
            with open(token_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return ""
    return ""


def _github_headers(token):
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _github_base_url(base_url=None):
    return base_url or "https://api.github.com"


def github_request(method, path, token, base_url=None, params=None, payload=None):
    url = _github_base_url(base_url).rstrip("/") + "/" + path.lstrip("/")
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=_github_headers(token),
            params=params,
            json=payload,
            timeout=30
        )
        if response.status_code >= 200 and response.status_code < 300:
            if response.text:
                try:
                    return {"status": "success", "data": response.json()}
                except Exception:
                    return {"status": "success", "data": response.text}
            return {"status": "success", "data": None}
        try:
            error_data = response.json()
        except Exception:
            error_data = response.text
        return {
            "status": "error",
            "message": f"GitHub API 错误: {response.status_code}",
            "status_code": response.status_code,
            "data": error_data
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def get_authenticated_user(token, base_url=None):
    return github_request("GET", "/user", token, base_url=base_url)


def read_local_file_base64(file_path):
    if not file_path or not os.path.isfile(file_path):
        return {"status": "error", "message": "本地文件不存在"}
    try:
        with open(file_path, "rb") as f:
            raw = f.read()
        encoded = base64.b64encode(raw).decode("utf-8")
        return {"status": "success", "data": encoded}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def build_json_payload(content):
    try:
        return json.loads(json.dumps(content, ensure_ascii=False))
    except Exception:
        return content


def parse_repo_url(repo_url):
    if not repo_url:
        return "", ""
    raw = str(repo_url).strip().strip("\"")
    if not raw:
        return "", ""
    if raw.startswith("git@"):
        raw = raw.split(":", 1)[1] if ":" in raw else raw.split("@", 1)[1]
    if raw.endswith(".git"):
        raw = raw[:-4]
    if "://" in raw:
        parsed = urlparse(raw)
        raw = parsed.netloc + parsed.path
    raw = raw.strip("/").replace("\\", "/")
    if raw.startswith("github.com/"):
        raw = raw[len("github.com/"):]
    parts = [p for p in raw.split("/") if p]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return "", ""
