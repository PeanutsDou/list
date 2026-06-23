
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from ai_files_tools.ai_files_read import (
    resolve_target_path
)

def open_file(path):
    if not path:
        return {"success": False, "reason": "path_empty", "message": "路径不能为空"}

    # 解析目标路径
    target_path = resolve_target_path(path)
    
    if not target_path or not os.path.exists(target_path):
        return {"success": False, "reason": "not_found", "path": target_path or path, "message": "文件或文件夹不存在"}

    try:
        os.startfile(target_path)
        return {"success": True, "path": path, "target_path": target_path, "message": "打开成功"}
    except Exception as e:
        return {
            "success": False,
            "reason": "open_failed",
            "path": target_path,
            "error": str(e),
            "message": f"打开失败: {str(e)}"
        }
