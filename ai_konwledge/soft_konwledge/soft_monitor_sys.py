import time
import json
import os
import sys
import subprocess
from datetime import datetime

try:
    import uiautomation as auto
except ImportError:
    print("错误: 缺少依赖库 'uiautomation'。请运行 'pip install uiautomation' 安装。")
    sys.exit(1)

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(DATA_DIR, "konwledge.json")
CONFIG_FILE = os.path.join(DATA_DIR, "monitor_config.json")
CHECK_INTERVAL = 2
SAVE_INTERVAL = 10

_process_cache = {}


def is_monitoring_enabled():
    if not os.path.exists(CONFIG_FILE):
        return True
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("enabled", True)
    except Exception:
        return True


def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return []


def save_data(data):
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _query_process_field(pid, field):
    try:
        command = f"(Get-Process -Id {int(pid)}).{field}"
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            check=False
        )
        return (result.stdout or "").strip()
    except Exception:
        return ""


def _get_process_info(pid):
    if not pid:
        return {"process_id": pid, "process_name": "", "exe_path": ""}
    now = time.time()
    cached = _process_cache.get(pid)
    if cached and now - cached["time"] < 60:
        return cached["info"]
    info = {"process_id": pid, "process_name": "", "exe_path": ""}
    try:
        import psutil
        proc = psutil.Process(pid)
        info["process_name"] = proc.name() or ""
        try:
            info["exe_path"] = proc.exe() or ""
        except Exception:
            info["exe_path"] = ""
    except Exception:
        info["process_name"] = _query_process_field(pid, "ProcessName")
        info["exe_path"] = _query_process_field(pid, "Path")
    _process_cache[pid] = {"time": now, "info": info}
    return info


def _build_window_info(window):
    try:
        title = window.Name or ""
        class_name = window.ClassName or ""
        process_id = getattr(window, "ProcessId", None)
        handle = getattr(window, "NativeWindowHandle", None)
        process_info = _get_process_info(process_id)
        process_name = process_info.get("process_name", "")
        exe_path = process_info.get("exe_path", "")
        app_name = process_name or title
        if not title and not process_name:
            return None
        return {
            "title": title,
            "class_name": class_name,
            "process_id": process_id,
            "process_name": process_name,
            "exe_path": exe_path,
            "window_handle": handle,
            "app_name": app_name
        }
    except Exception:
        return None


def get_active_app_info():
    try:
        window = auto.GetForegroundControl()
        if not window:
            return None
        info = _build_window_info(window)
        if not info:
            return None
        if info.get("title", "") == "Program Manager":
            return None
        return info
    except Exception:
        return None


def get_all_app_windows_info():
    results = []
    try:
        root = auto.GetRootControl()
        windows = root.GetChildren()
        for window in windows:
            if window.ControlTypeName != "WindowControl":
                continue
            try:
                if hasattr(window, "IsVisible") and not window.IsVisible:
                    continue
            except Exception:
                pass
            info = _build_window_info(window)
            if not info:
                continue
            if info.get("title", "") == "Program Manager":
                continue
            results.append(info)
    except Exception:
        return []
    return results


def build_record(info, current_time):
    return {
        "title": info.get("title", ""),
        "app_name": info.get("app_name", ""),
        "process_name": info.get("process_name", ""),
        "process_id": info.get("process_id"),
        "exe_path": info.get("exe_path", ""),
        "window_handle": info.get("window_handle"),
        "start_time": current_time.isoformat(),
        "end_time": current_time.isoformat(),
        "duration": 0.0,
        "front_duration": 0.0,
        "background_duration": 0.0
    }


def update_record_state(record, current_time, new_state, state_cache, key):
    cache = state_cache.get(key)
    if cache is None:
        state_cache[key] = {"state": new_state, "time": current_time}
        record["end_time"] = current_time.isoformat()
        return
    delta = (current_time - cache["time"]).total_seconds()
    if cache["state"] == "front":
        record["front_duration"] += delta
    else:
        record["background_duration"] += delta
    record["duration"] = record["front_duration"] + record["background_duration"]
    record["end_time"] = current_time.isoformat()
    cache["state"] = new_state
    cache["time"] = current_time


def close_record(record, current_time, state_cache, key):
    cache = state_cache.get(key)
    if cache is None:
        record["end_time"] = current_time.isoformat()
        return
    update_record_state(record, current_time, cache["state"] or "background", state_cache, key)
    state_cache.pop(key, None)


def _build_key(item):
    process_id = item.get("process_id")
    handle = item.get("window_handle")
    if process_id is None and handle is None:
        return item.get("title", "")
    return f"{process_id}:{handle}"


def main():
    print("开始运行软件监控系统...")
    print(f"数据文件路径: {DATA_FILE}")
    current_data = load_data()
    open_records = {}
    state_cache = {}
    last_save_time = time.time()
    last_data_mtime = os.path.getmtime(DATA_FILE) if os.path.exists(DATA_FILE) else None
    try:
        while True:
            if not is_monitoring_enabled():
                current_time = datetime.now()
                for key, record in list(open_records.items()):
                    close_record(record, current_time, state_cache, key)
                open_records.clear()
                save_data(current_data)
                time.sleep(CHECK_INTERVAL)
                continue
            if os.path.exists(DATA_FILE):
                current_mtime = os.path.getmtime(DATA_FILE)
                if last_data_mtime is None or current_mtime > last_data_mtime:
                    disk_data = load_data()
                    if not disk_data:
                        current_data = []
                        open_records = {}
                        state_cache = {}
                    last_data_mtime = current_mtime
            info = get_active_app_info()
            windows_info = get_all_app_windows_info()
            current_time = datetime.now()
            windows_map = {}
            for item in windows_info:
                key = _build_key(item)
                if key and key not in windows_map:
                    windows_map[key] = item
            current_keys = set(windows_map.keys())
            for key in list(open_records.keys()):
                if key not in current_keys:
                    close_record(open_records[key], current_time, state_cache, key)
                    open_records.pop(key, None)
            for key in current_keys:
                if key not in open_records:
                    record = build_record(windows_map[key], current_time)
                    open_records[key] = record
                    current_data.append(record)
            front_key = _build_key(info) if info else None
            for key, record in open_records.items():
                new_state = "front" if key == front_key else "background"
                update_record_state(record, current_time, new_state, state_cache, key)
            if time.time() - last_save_time > SAVE_INTERVAL:
                if current_data:
                    save_data(current_data)
                    last_save_time = time.time()
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\n停止监控。")
        current_time = datetime.now()
        for key, record in list(open_records.items()):
            close_record(record, current_time, state_cache, key)
        save_data(current_data)
        print("数据已保存。")


if __name__ == "__main__":
    main()
