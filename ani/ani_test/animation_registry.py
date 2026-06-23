import os
import json
from typing import Dict, List, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
REGISTRY_PATH = os.path.join(current_dir, "animation_registry.json")

DEFAULT_REGISTRY = {
    "default": "sleep_series",
    "animations": {
        "walk": {
            "frames_dir": "ani/走路动画",
            "pattern": "{index:02d}.png",
            "start": 1,
            "end": 4,
            "loop": True,
            "interval_ms": 120
        },
        "takeoff": {
            "frames_dir": "ani/飞行动画/起飞",
            "pattern": "{index:02d}.png",
            "start": 1,
            "end": 16,
            "loop": False,
            "interval_ms": 120
        },
        "hover": {
            "frames_dir": "ani/飞行动画/滞空",
            "pattern": "{index:02d}.png",
            "start": 1,
            "end": 3,
            "loop": True,
            "interval_ms": 200
        },
        "sleep": {
            "frames_dir": "ani/睡觉动画",
            "pattern": "{index:02d}.png",
            "start": 1,
            "end": 20,
            "loop": False,
            "interval_ms": 120
        },
        "sleep_idle": {
            "frames_dir": "ani/睡觉待机动画",
            "pattern": "{index:02d}.png",
            "start": 1,
            "end": 9,
            "loop": True,
            "interval_ms": 120
        }
    },
    "sequences": {
        "takeoff_hover": {
            "items": [
                {"name": "takeoff"},
                {"name": "hover"}
            ]
        },
        "sleep_series": {
            "items": [
                {"name": "sleep", "loop": False},
                {"name": "sleep_idle", "loop": True}
            ]
        }
    }
}


def _load_registry() -> Dict:
    if not os.path.exists(REGISTRY_PATH):
        return DEFAULT_REGISTRY
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else DEFAULT_REGISTRY
    except Exception:
        return DEFAULT_REGISTRY


def get_default_sequence_name() -> Optional[str]:
    data = _load_registry()
    default_name = data.get("default")
    return default_name if isinstance(default_name, str) else None


def _resolve_frames_dir(frames_dir: str) -> str:
    if os.path.isabs(frames_dir):
        return frames_dir
    return os.path.join(project_root, frames_dir)


def _build_frame_paths(config: Dict) -> List[str]:
    frames_dir = _resolve_frames_dir(str(config.get("frames_dir", "")))
    pattern = str(config.get("pattern", "{index:02d}.png"))
    start = int(config.get("start", 1))
    end = int(config.get("end", 1))
    if start > end:
        start, end = end, start
    paths = []
    for index in range(start, end + 1):
        name = pattern.format(index=index)
        path = os.path.join(frames_dir, name)
        if os.path.exists(path):
            paths.append(path)
    return paths


def get_sequence_items(name: str) -> List[Dict]:
    data = _load_registry()
    animations = data.get("animations", {})
    sequences = data.get("sequences", {})
    result_items = []

    if name in sequences:
        items = sequences.get(name, {}).get("items", [])
        for item in items:
            anim_name = item.get("name")
            anim_config = animations.get(anim_name, {})
            if not isinstance(anim_config, dict):
                continue
            frame_paths = _build_frame_paths(anim_config)
            if not frame_paths:
                continue
            interval_ms = int(item.get("interval_ms", anim_config.get("interval_ms", 120)))
            loop = bool(item.get("loop", anim_config.get("loop", True)))
            result_items.append({
                "name": anim_name,
                "frame_paths": frame_paths,
                "interval_ms": interval_ms,
                "loop": loop
            })
        return result_items

    anim_config = animations.get(name, {})
    if isinstance(anim_config, dict):
        frame_paths = _build_frame_paths(anim_config)
        if frame_paths:
            result_items.append({
                "name": name,
                "frame_paths": frame_paths,
                "interval_ms": int(anim_config.get("interval_ms", 120)),
                "loop": bool(anim_config.get("loop", True))
            })
    return result_items
