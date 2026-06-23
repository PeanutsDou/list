import os
import sys
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from ani.ani_test.animation_registry import get_default_sequence_name
except Exception:
    get_default_sequence_name = None


def _get_registry_path() -> str:
    return os.path.join(project_root, "ani", "ani_test", "animation_registry.json")


def _load_registry() -> dict:
    path = _get_registry_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _get_sequences() -> list:
    data = _load_registry()
    sequences = data.get("sequences", {})
    return list(sequences.keys()) if isinstance(sequences, dict) else []


def _get_state_path() -> str:
    return os.path.join(project_root, "ani", "animation_state.json")


def _load_state() -> dict:
    path = _get_state_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state(data: dict) -> None:
    path = _get_state_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return None


def _normalize_play_mode(value: str) -> str:
    return value if value in ("manual", "random") else "manual"


def get_pet_status() -> dict:
    state = _load_state()
    play_mode = _normalize_play_mode(state.get("play_mode", "manual"))
    current_sequence = state.get("current_sequence")
    if not current_sequence and callable(get_default_sequence_name):
        current_sequence = get_default_sequence_name()
    return {
        "success": True,
        "current_sequence": current_sequence,
        "play_mode": play_mode,
        "available_sequences": _get_sequences()
    }


def get_pet_features() -> dict:
    return {
        "success": True,
        "features": ["切换动画", "随机播放", "查询状态", "查看可用动画"],
        "available_sequences": _get_sequences(),
        "play_modes": ["manual", "random"]
    }


def set_pet_animation(sequence_name: str, play_mode: str = "manual",
                      random_weights: dict = None, random_interval: dict = None) -> dict:
    if not sequence_name:
        return {"success": False, "message": "动画名称不能为空"}
    available_sequences = _get_sequences()
    if available_sequences and sequence_name not in available_sequences:
        return {
            "success": False,
            "message": "动画名称不存在",
            "available_sequences": available_sequences
        }
    state = _load_state()
    state["current_sequence"] = sequence_name
    state["play_mode"] = _normalize_play_mode(play_mode)
    if isinstance(random_weights, dict) and random_weights:
        state["random_weights"] = random_weights
    if isinstance(random_interval, dict) and random_interval:
        state["random_interval"] = random_interval
    _save_state(state)
    return {
        "success": True,
        "current_sequence": sequence_name,
        "play_mode": state.get("play_mode", "manual")
    }
