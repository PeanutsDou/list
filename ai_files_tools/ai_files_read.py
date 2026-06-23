
import os
import datetime
import subprocess
import urllib.parse
import winreg
import sys
import string
import ctypes

def get_drives():
    """获取系统中所有可用的盘符（Windows）"""
    drives = []
    try:
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drives.append(f"{letter}:\\")
            bitmask >>= 1
    except Exception:
        pass
    return drives

def resolve_desktop_path():
    """获取桌面绝对路径"""
    # 1. 尝试通过注册表获取精确的桌面路径 (Windows)
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
        desktop_path, _ = winreg.QueryValueEx(key, "Desktop")
        if desktop_path and os.path.isdir(desktop_path):
            return desktop_path
    except Exception:
        pass

    candidates = []
    home = os.path.expanduser("~")
    if home:
        candidates.append(os.path.join(home, "Desktop"))
        candidates.append(os.path.join(home, "桌面"))
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        candidates.append(os.path.join(user_profile, "Desktop"))
        candidates.append(os.path.join(user_profile, "桌面"))

    for path in candidates:
        if path and os.path.isdir(path):
            return path
            
    return None

def validate_path_security(path):
    """
    验证路径安全性。
    
    重构说明：
    根据用户需求，移除了仅限桌面的限制。
    现在允许访问本地任何合法的绝对路径。
    仍然保留基本检查以防止空路径或非法字符。
    """
    if not path:
        return False
    
    # 转换为字符串并清理
    raw_path = str(path).strip().strip("\"")
    
    # 检查是否包含空字节（安全隐患）
    if '\0' in raw_path:
        return False
        
    return True

def resolve_target_path(path):
    """
    解析目标路径为绝对路径。
    
    逻辑：
    1. 处理 "Desktop"/"桌面" 别名。
    2. 处理快捷方式 (.lnk, .url)。
    3. 如果是相对路径，默认相对于桌面解析（为了兼容性），但如果路径存在则优先返回。
    4. 确保返回的是绝对路径。
    """
    if not path:
        return None
        
    raw_path = str(path).strip().strip("\"")
    lower_path = raw_path.lower()
    
    # 1. 处理别名
    if lower_path in ["desktop", "桌面"]:
        return resolve_desktop_path()

    # 2. 处理快捷方式 (如果是文件)
    if os.path.isfile(raw_path):
        if lower_path.endswith(".lnk"):
            target = _resolve_lnk_target(raw_path)
            if target:
                return os.path.abspath(target)
        elif lower_path.endswith(".url"):
            target = _resolve_url_target(raw_path)
            if target:
                return os.path.abspath(target)
                
    # 3. 路径存在性与绝对化
    # 扩展环境变量 (如 %APPDATA%)
    expanded_path = os.path.expandvars(raw_path)
    expanded_path = os.path.expanduser(expanded_path)
    
    if os.path.isabs(expanded_path):
        return os.path.abspath(os.path.normpath(expanded_path))
        
    # 如果是相对路径，尝试在当前工作目录查找
    # 注意：在工具上下文中，CWD 可能不是用户期望的，但对于 "相对路径" 这是一个标准解释。
    # 考虑到用户习惯，我们也可以优先检查 "桌面 + 相对路径"
    
    desktop_path = resolve_desktop_path()
    if desktop_path:
        desktop_candidate = os.path.join(desktop_path, expanded_path)
        if os.path.exists(desktop_candidate):
            return os.path.abspath(os.path.normpath(desktop_candidate))
            
    # 如果桌面下没有，则返回相对于 CWD 的绝对路径 (即使不存在，因为可能是要创建的文件)
    return os.path.abspath(os.path.normpath(expanded_path))

def _resolve_lnk_target(path):
    try:
        # 使用 PowerShell 解析 LNK
        escaped = path.replace("'", "''")
        command = f"(New-Object -ComObject WScript.Shell).CreateShortcut('{escaped}').TargetPath"
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            check=False
        )
        target = (result.stdout or "").strip()
        return target or None
    except Exception:
        return None

def _resolve_url_target(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.lower().startswith("url="):
                    url = line[4:].strip()
                    if url.lower().startswith("file:///"):
                        raw = url[8:]
                        raw = urllib.parse.unquote(raw)
                        return raw.replace("/", os.sep)
                    return None
        return None
    except Exception:
        return None

def read_directory_items(directory_path):
    """读取指定目录下的所有项目"""
    items = []
    if not directory_path or not os.path.isdir(directory_path):
        return items
    try:
        with os.scandir(directory_path) as entries:
            for entry in entries:
                info = _build_item_info(entry)
                if info:
                    items.append(info)
    except Exception:
        items = []

    items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    return items

def read_desktop_files():
    """
    读取桌面文件列表。
    
    功能说明:
    该函数用于获取当前用户桌面的路径，并读取桌面上的所有文件和文件夹列表。
    它首先解析桌面的绝对路径，然后调用 read_directory_items 函数获取该路径下的内容详情。
    
    返回值:
    返回一个字典，包含以下字段:
    - "desktop_path": 桌面的绝对路径字符串。
    - "items": 一个列表，包含桌面下所有文件和文件夹的详细信息字典。
    
    注意:
    保留此函数主要是为了维持与 skill_registry.py 等旧模块的向后兼容性。
    """
    desktop_path = resolve_desktop_path()
    items = read_directory_items(desktop_path)
    return {
        "desktop_path": desktop_path,
        "items": items
    }

def _build_item_info(entry):
    try:
        raw_path = entry.path
        raw_name = entry.name
        is_dir = entry.is_dir()
        
        is_shortcut = raw_name.lower().endswith(('.lnk', '.url'))
        is_executable = raw_name.lower().endswith(('.exe', '.bat', '.cmd', '.msi'))
        
        size_bytes = 0
        modified_time = ""
        try:
            stat = entry.stat()
            size_bytes = stat.st_size if not is_dir else 0
            modified_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            stat = None
        
        return {
            "name": raw_name,
            "path": raw_path,
            "is_dir": is_dir,
            "is_shortcut": is_shortcut,
            "is_executable": is_executable,
            "size_text": _format_size(size_bytes) if not is_dir else "",
            "modified_time": modified_time
        }
    except Exception:
        return None

def _build_item_info_from_path(path, source_path=None, source_name=None):
    try:
        stat = os.stat(path)
        is_dir = os.path.isdir(path)
        size_bytes = stat.st_size if not is_dir else 0
        name = os.path.basename(path) or path
        
        is_shortcut = name.lower().endswith(('.lnk', '.url'))
        is_executable = name.lower().endswith(('.exe', '.bat', '.cmd', '.msi'))
        
        return {
            "name": name,
            "path": path,
            "is_dir": is_dir,
            "is_shortcut": is_shortcut,
            "is_executable": is_executable,
            "size_bytes": size_bytes,
            "size_text": _format_size(size_bytes) if not is_dir else "",
            "modified_time": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "source_path": source_path,
            "source_name": source_name,
            "target_path": path if source_path and source_path != path else None
        }
    except Exception:
        return None

def build_item_info_from_path(path):
    return _build_item_info_from_path(path)

def _format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def resolve_desktop_entry_path_by_name(name):
    """
    为了兼容性保留，但在新架构下，建议直接使用 search 功能。
    这个函数只在桌面上查找。
    """
    if not name:
        return None
    desktop_path = resolve_desktop_path()
    if not desktop_path:
        return None
    target_name = str(name).strip().strip("\"")
    target_lower = target_name.lower()
    
    # 直接拼接尝试
    direct = os.path.join(desktop_path, target_name)
    if os.path.exists(direct):
        return direct
        
    # 模糊查找
    try:
        with os.scandir(desktop_path) as entries:
            candidates = []
            for entry in entries:
                if entry.name.lower() == target_lower:
                    return entry.path
                if os.path.splitext(entry.name)[0].lower() == os.path.splitext(target_name)[0].lower():
                    candidates.append(entry)
            
            # 优先选择快捷方式
            for c in candidates:
                if c.name.lower().endswith(('.lnk', '.url')):
                    return c.path
            if candidates:
                return candidates[0].path
    except:
        pass
    return None

def find_in_desktop_tree(name, extensions=None):
    """保留用于桌面递归查找"""
    # 逻辑同原版，不再赘述，但可以考虑复用 search 模块的逻辑
    # 为了保持最小改动，暂时保留原实现逻辑
    if not name:
        return None
    desktop_path = resolve_desktop_path()
    if not desktop_path:
        return None
        
    raw_name = str(name).strip().strip("\"")
    if os.sep in raw_name or "/" in raw_name:
        raw_name = os.path.basename(raw_name)
        
    target_lower = raw_name.lower()
    target_compact = target_lower.replace(" ", "").replace("\u3000", "")
    
    normalized_extensions = None
    if extensions:
        if isinstance(extensions, (list, tuple, set)):
            normalized_extensions = {str(ext).lower() for ext in extensions if ext}
        else:
            normalized_extensions = {str(extensions).lower()}

    for root, dirs, files in os.walk(desktop_path):
        # 简化匹配逻辑...
        for filename in files:
            file_lower = filename.lower()
            if normalized_extensions and os.path.splitext(file_lower)[1] not in normalized_extensions:
                continue
            
            file_compact = file_lower.replace(" ", "")
            if (file_lower == target_lower or 
                os.path.splitext(file_lower)[0] == os.path.splitext(target_lower)[0] or
                file_compact == target_compact):
                return os.path.join(root, filename)
    return None
