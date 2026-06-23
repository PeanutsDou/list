
"""
文件复制技能模块：
提供在本地任意路径复制文件的能力。
"""
import os
import sys
import shutil

# 确保能导入当前目录下的模块
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from ai_files_tools.ai_files_read import (
    resolve_desktop_path,
    resolve_target_path,
    validate_path_security
)


def copy_file(source_path, target_path=None, overwrite=False):
    """
    复制文件到指定路径或目录。

    Args:
        source_path (str): 源文件路径或文件名。
        target_path (str, optional): 目标路径或目录路径。不传则默认桌面。
        overwrite (bool, optional): 是否允许覆盖目标文件，默认 False。

    Returns:
        dict: 包含操作结果的信息。
    """
    if not source_path:
        return {"success": False, "reason": "source_path_empty", "message": "源路径不能为空"}

    # 解析源文件真实路径
    real_source = resolve_target_path(source_path)
    if not real_source or not os.path.exists(real_source):
        return {"success": False, "reason": "source_not_found", "message": f"源文件不存在: {source_path}"}

    # 只允许复制文件
    if not os.path.isfile(real_source):
        return {"success": False, "reason": "source_not_file", "path": real_source, "message": "源路径不是文件"}

    # 解析目标路径
    destination = _resolve_destination_path(real_source, target_path)
    if not destination:
        return {"success": False, "reason": "target_invalid", "message": "目标路径无效或父目录不存在"}

    # 防止复制到自身
    if os.path.abspath(real_source) == os.path.abspath(destination):
        return {"success": False, "reason": "same_path", "path": destination, "message": "源文件与目标文件相同"}

    # 已存在且不允许覆盖
    if os.path.exists(destination) and not overwrite:
        return {"success": False, "reason": "destination_exists", "path": destination, "message": "目标文件已存在"}

    try:
        # 执行复制，保留原文件元数据
        shutil.copy2(real_source, destination)
        return {
            "success": True,
            "source": real_source,
            "destination": destination,
            "message": "复制成功"
        }
    except Exception as e:
        return {"success": False, "reason": "copy_failed", "error": str(e), "message": f"复制失败: {str(e)}"}


def _resolve_destination_path(real_source, target_path):
    """
    根据目标输入解析最终目标文件路径。
    """
    if target_path:
        resolved_target = resolve_target_path(target_path)
    else:
        resolved_target = resolve_desktop_path()

    if not resolved_target:
        return None

    resolved_target = os.path.abspath(os.path.normpath(resolved_target))

    # 目标为目录时，保持文件名不变
    if os.path.isdir(resolved_target):
        return os.path.join(resolved_target, os.path.basename(real_source))

    # 目标为文件路径时，校验父目录是否存在
    parent_dir = os.path.dirname(resolved_target)
    if parent_dir and not os.path.exists(parent_dir):
        return None

    return resolved_target
