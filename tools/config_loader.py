import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def get_llm_config():
    return load_config().get("llm", {})

def get_email_config():
    return load_config().get("email", {})

def get_github_config():
    return load_config().get("github", {})
