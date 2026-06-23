import time
import json
import os
import sys
from datetime import datetime, timedelta

# 尝试导入 uiautomation，如果不存在则提示
try:
    import uiautomation as auto
except ImportError:
    print("错误: 缺少依赖库 'uiautomation'。请运行 'pip install uiautomation' 安装。")
    sys.exit(1)

# 配置
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(DATA_DIR, "konwledge.json")
CONFIG_FILE = os.path.join(DATA_DIR, "monitor_config.json")
CHECK_INTERVAL = 2  # 检查间隔（秒）
SAVE_INTERVAL = 10   # 自动保存间隔（秒）

def is_monitoring_enabled():
    """检查监控开关状态"""
    if not os.path.exists(CONFIG_FILE):
        return True # 默认开启
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get('enabled', True)
    except Exception:
        return True

def load_data():
    """加载现有知识库数据"""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return []

def save_data(data):
    """保存数据到知识库"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"保存数据失败: {e}")

def get_active_browser_info():
    """获取当前活动窗口的浏览器信息"""
    try:
        # 获取当前前台窗口
        window = auto.GetForegroundControl()
        if not window:
            return None

        title = window.Name
        class_name = window.ClassName
        
        # 简单的浏览器识别逻辑
        browser_type = None
        if "Chrome" in class_name or "Google Chrome" in title:
            browser_type = "Chrome"
        elif "Edge" in class_name or "Microsoft Edge" in title:
            browser_type = "Edge"
        elif "Firefox" in class_name or "Mozilla Firefox" in title:
            browser_type = "Firefox"
        
        if not browser_type:
            return None

        # 排除非浏览器内容的窗口（如开发工具等，视情况而定）
        
        url = "Unknown"
        # 尝试获取 URL (针对 Chrome/Edge)
        # 限制搜索深度和范围以提高性能
        try:
            # 常见浏览器的地址栏通常是 EditControl
            # 注意：不同版本浏览器结构可能不同，这里使用通用的模糊匹配
            address_bar = window.EditControl(searchDepth=12, RegexName=".*地址.*|.*Address.*|.*搜索.*|.*Search.*|.*Location.*")
            
            if address_bar.Exists(0, 0):
                # 尝试通过 ValuePattern 获取
                if hasattr(address_bar, 'GetValuePattern'):
                    pattern = address_bar.GetValuePattern()
                    if pattern:
                        url = pattern.Value
                
                # 兼容性尝试 (LegacyIAccessible)
                if (not url or url == "Unknown") and hasattr(address_bar, 'GetLegacyIAccessiblePattern'):
                    pattern = address_bar.GetLegacyIAccessiblePattern()
                    if pattern:
                        url = pattern.Value
        except Exception:
            pass

        # 格式化 URL
        if url and url != "Unknown":
            url = url.strip()
            # 如果是搜索词而非 URL，可能需要特殊处理，这里暂时保留原样或简单判断
            if not url.startswith(("http://", "https://", "file://", "chrome://", "edge://", "about:")):
                if "." in url and " " not in url:
                    url = "https://" + url
        
        # 严格过滤：如果没有获取到有效URL，或者URL不是以http/https开头，则忽略
        # 这可以有效排除非浏览器窗口（如IDE、Electron应用等）以及浏览器的新标签页/设置页等杂质
        if not url or url == "Unknown" or not url.startswith(("http://", "https://")):
            return None

        return {
            "title": title,
            "url": url,
            "browser_type": browser_type,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        # print(f"获取窗口信息出错: {e}")
        return None

def get_all_browser_windows_info():
    results = []
    try:
        root = auto.GetRootControl()
        windows = root.GetChildren()
        for window in windows:
            if window.ControlTypeName != "WindowControl":
                continue

            title = window.Name
            class_name = window.ClassName
            browser_type = None

            if "Chrome" in class_name or "Google Chrome" in title:
                browser_type = "Chrome"
            elif "Edge" in class_name or "Microsoft Edge" in title:
                browser_type = "Edge"
            elif "Firefox" in class_name or "Mozilla Firefox" in title:
                browser_type = "Firefox"
            else:
                continue

            if "Trae" in title or "Visual Studio Code" in title:
                continue

            url = "Unknown"
            try:
                address_bar = window.EditControl(searchDepth=12, RegexName=".*地址.*|.*Address.*|.*搜索.*|.*Search.*|.*Location.*")
                if address_bar.Exists(0, 0):
                    if hasattr(address_bar, 'GetValuePattern'):
                        pattern = address_bar.GetValuePattern()
                        if pattern:
                            url = pattern.Value
                    if (not url or url == "Unknown") and hasattr(address_bar, 'GetLegacyIAccessiblePattern'):
                        pattern = address_bar.GetLegacyIAccessiblePattern()
                        if pattern:
                            url = pattern.Value
            except Exception:
                pass

            if url and url != "Unknown":
                url = url.strip()
                if not url.startswith(("http://", "https://", "file://", "chrome://", "edge://", "about:")):
                    if "." in url and " " not in url:
                        url = "https://" + url

            if not url or url == "Unknown" or not url.startswith(("http://", "https://")):
                continue

            results.append({
                "title": title,
                "url": url,
                "browser_type": browser_type
            })
    except Exception:
        return []

    return results

def build_record(info, current_time):
    return {
        "url": info["url"],
        "title": info["title"],
        "browser_type": info["browser_type"],
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

def main():
    print(f"开始运行网页监控系统...")
    print(f"数据文件路径: {DATA_FILE}")
    
    current_data = load_data()
    open_records = {}
    state_cache = {}
    last_save_time = time.time()
    last_data_mtime = os.path.getmtime(DATA_FILE) if os.path.exists(DATA_FILE) else None
    
    # 如果已有数据，尝试恢复上下文（可选，这里简单起见重新开始或接续）
    if current_data:
        # 检查最后一条是否是未完成的会话（例如没有 end_time 或 duration）
        # 这里假设 konwledge.json 记录的是已完成的片段或包含持续时间
        pass

    try:
        while True:
            if not is_monitoring_enabled():
                current_time = datetime.now()
                for url, record in list(open_records.items()):
                    close_record(record, current_time, state_cache, url)
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

            info = get_active_browser_info()
            windows_info = get_all_browser_windows_info()
            current_time = datetime.now()
            windows_map = {}
            for item in windows_info:
                url = item.get("url")
                if url and url not in windows_map:
                    windows_map[url] = item
            current_urls = set(windows_map.keys())

            for url in list(open_records.keys()):
                if url not in current_urls:
                    close_record(open_records[url], current_time, state_cache, url)
                    open_records.pop(url, None)

            for url in current_urls:
                if url not in open_records:
                    record = build_record(windows_map[url], current_time)
                    open_records[url] = record
                    current_data.append(record)

            front_url = info.get("url") if info else None
            for url, record in open_records.items():
                new_state = "front" if url == front_url else "background"
                update_record_state(record, current_time, new_state, state_cache, url)
            
            # 定时保存
            if time.time() - last_save_time > SAVE_INTERVAL:
                if current_data:
                    save_data(current_data)
                    last_save_time = time.time()
            
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\n停止监控。")
        current_time = datetime.now()
        for url, record in list(open_records.items()):
            close_record(record, current_time, state_cache, url)
        save_data(current_data)
        print("数据已保存。")

if __name__ == "__main__":
    main()
