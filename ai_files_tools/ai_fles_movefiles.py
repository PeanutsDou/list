import os
import sys
import shutil

# 确保能导入当前目录下的模块
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from ai_files_tools.ai_files_read import resolve_desktop_path, resolve_target_path, validate_path_security, resolve_desktop_entry_path_by_name

def move_file(source_path, target_path=None):
    """
    移动文件从一个路径到另一个路径。
    
    Args:
        source_path (str): 源文件路径。
        target_path (str, optional): 目标路径。可以是目录（移入其中）或完整文件路径（移动并重命名）。
                                     如果未提供，默认为桌面。
    
    Returns:
        dict: 包含操作结果的信息。
    """
    if not source_path:
        return {"success": False, "reason": "source_path_empty", "message": "源路径不能为空"}

    # 解析源路径
    normalized_source = source_path.strip().strip("\"")
    if not os.path.isabs(normalized_source):
        desktop_path = resolve_desktop_path()
        if desktop_path:
            candidate_path = os.path.join(desktop_path, normalized_source)
            if os.path.exists(candidate_path):
                normalized_source = candidate_path
    if os.path.exists(normalized_source):
        real_source = os.path.abspath(os.path.normpath(normalized_source))
    else:
        # 优先使用快捷方式匹配逻辑
        desktop_match = resolve_desktop_entry_path_by_name(normalized_source)
        if desktop_match and os.path.exists(desktop_match):
            real_source = os.path.abspath(os.path.normpath(desktop_match))
        else:
            real_source = resolve_target_path(normalized_source) or normalized_source
            
    if not os.path.exists(real_source):
        return {"success": False, "reason": "source_not_found", "path": real_source, "message": "源文件不存在"}

    # 安全检查：禁止操作真实可执行文件（.exe, .bat, .cmd, .msi），除非用户明确提供了扩展名
    # 如果 source_path 没有提供扩展名，但解析出的 real_source 是可执行文件，
    # 且存在同名的快捷方式（虽然 resolve_desktop_entry_path_by_name 已经优先匹配快捷方式），
    # 这里做一个双重保险：如果用户给的是模糊名称，坚决不操作 exe
    
    source_ext = os.path.splitext(real_source)[1].lower()
    input_ext = os.path.splitext(normalized_source)[1].lower()
    
    # 定义危险扩展名
    dangerous_exts = {'.exe', '.bat', '.cmd', '.msi', '.com', '.scr'}
    
    if source_ext in dangerous_exts:
        # 如果用户输入没有带后缀，或者是模糊匹配到的 exe，则拒绝操作
        # 除非用户明确输入了 "xxx.exe"
        if not input_ext: 
             return {
                "success": False, 
                "reason": "security_restriction", 
                "path": real_source, 
                "message": f"安全警告：检测到目标是可执行文件({source_ext})。为防止误操作启动器，请提供完整文件名（包含后缀）以确认操作，或检查是否想操作同名快捷方式。"
            }

    # 安全检查：限制不安全路径
    if not validate_path_security(real_source):
        return {
            "success": False, 
            "reason": "security_violation", 
            "path": real_source, 
            "message": "安全限制：路径不允许访问"
        }

    # 确定目标路径
    if target_path:
        real_target = resolve_target_path(target_path) or target_path
    else:
        real_target = resolve_desktop_path()
    if not real_target:
        return {"success": False, "reason": "desktop_not_found", "message": "无法定位桌面路径"}

    # 检查目标路径父目录是否存在（如果目标是文件路径）
    # 或者如果目标是目录，检查目录是否存在
    
    destination = real_target
    
    # 如果目标是一个已存在的目录，则移动到该目录下，文件名保持不变
    if os.path.isdir(real_target):
        destination = os.path.join(real_target, os.path.basename(real_source))
    else:
        # 如果目标不存在，或者不是目录，假设它是目标文件路径
        # 检查其父目录是否存在
        target_dir = os.path.dirname(real_target)
        if target_dir and not os.path.exists(target_dir):
             return {"success": False, "reason": "target_parent_not_found", "path": target_dir, "message": "目标父目录不存在"}
        destination = real_target # 这里如果 real_target 不是目录，就把它当做完整目标路径

    # 安全检查：限制不安全路径
    if not validate_path_security(destination):
        return {
            "success": False, 
            "reason": "security_violation", 
            "path": destination, 
            "message": "安全限制：路径不允许访问"
        }

    # 检查目标文件是否已存在
    if os.path.exists(destination):
        return {"success": False, "reason": "destination_exists", "path": destination, "message": "目标位置已存在同名文件/文件夹"}

    try:
        shutil.move(real_source, destination)
        return {"success": True, "source": real_source, "destination": destination, "message": "移动成功"}
    except Exception as e:
        return {"success": False, "reason": "move_failed", "error": str(e), "message": f"移动失败: {str(e)}"}

def move_files_batch(moves_list):
    """
    批量移动文件。
    
    Args:
        moves_list (list): 包含移动信息的列表，每项为字典 {"source": "...", "target": "..."}。
                           "target" 可选，默认为桌面。
    
    Returns:
        list: 每个操作的结果列表。
    """
    results = []
    if not isinstance(moves_list, list):
        return {"success": False, "reason": "invalid_input", "message": "输入必须是列表"}

    for item in moves_list:
        if not isinstance(item, dict):
            results.append({"success": False, "reason": "invalid_item", "item": item, "message": "列表项必须是字典"})
            continue
            
        source = item.get("source")
        target = item.get("target")
        
        result = move_file(source, target)
        result["request"] = item
        results.append(result)
        
    return results
