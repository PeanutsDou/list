
"""
Excel 文件操作模块：
提供 csv 文件的创建、读取、更新、删除。
"""
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from ai_files_tools.ai_files_read import resolve_desktop_path, resolve_target_path, validate_path_security


def create_csv_file(file_name, columns=None, rows=None, parent_path=None):
    if not file_name:
        return {"success": False, "reason": "file_name_empty", "message": "文件名不能为空"}
    target_parent = _resolve_parent_path(parent_path)
    if not target_parent:
        return {"success": False, "reason": "parent_path_invalid", "message": "无法定位父目录"}
    safe_name = _ensure_extension(str(file_name).strip(), ".csv")
    full_path = os.path.join(target_parent, safe_name)
    
    if os.path.exists(full_path):
        return {"success": False, "reason": "already_exists", "path": full_path, "message": "目标文件已存在"}
    try:
        df = _build_dataframe(columns, rows)
        df.to_csv(full_path, index=False, encoding="utf-8-sig")
        return {"success": True, "path": full_path, "rows": len(df), "message": "创建成功"}
    except Exception as e:
        return {"success": False, "reason": "create_failed", "error": str(e), "message": f"创建失败: {str(e)}"}


def read_csv_file(file_path, max_rows=50):
    normalized = _normalize_existing_path(file_path, ".csv")
    if not normalized:
        return {"success": False, "reason": "path_invalid_or_not_found", "message": "路径无效或文件不存在"}
    try:
        df = _read_dataframe(normalized)
        preview = df.head(int(max_rows)).to_dict(orient="records")
        return {
            "success": True,
            "path": normalized,
            "rows": int(df.shape[0]),
            "columns": list(df.columns),
            "preview": preview
        }
    except Exception as e:
        return {"success": False, "reason": "read_failed", "error": str(e), "message": f"读取失败: {str(e)}"}


def update_csv_content(file_path, mode="replace", data=None, column=None, value=None):
    normalized = _normalize_existing_path(file_path, ".csv")
    if not normalized:
        return {"success": False, "reason": "path_invalid_or_not_found", "message": "路径无效或文件不存在"}
    mode = str(mode or "replace").lower()
    try:
        if mode == "replace":
            df = _build_dataframe(None, data)
        else:
            df = _read_dataframe(normalized)
            if mode == "append":
                if not data:
                    return {"success": False, "reason": "data_empty", "message": "追加数据不能为空"}
                append_df = _build_dataframe(None, data)
                df = _concat_dataframes(df, append_df)
            elif mode == "remove":
                if not column:
                    return {"success": False, "reason": "column_empty", "message": "删除条件列不能为空"}
                if column not in df.columns:
                    return {"success": False, "reason": "column_not_found", "message": "删除条件列不存在"}
                before = int(df.shape[0])
                # 注意：这里 value 的类型可能需要转换，目前只支持字符串比较
                df = df[df[column].astype(str) != str(value)]
                removed = before - int(df.shape[0])
                if removed == 0:
                    return {"success": False, "reason": "row_not_found", "message": "未找到匹配的行"}
            else:
                return {"success": False, "reason": "mode_invalid", "message": "不支持的更新模式"}
        df.to_csv(normalized, index=False, encoding="utf-8-sig")
        return {"success": True, "path": normalized, "rows": int(df.shape[0]), "mode": mode, "message": "内容已更新"}
    except Exception as e:
        return {"success": False, "reason": "update_failed", "error": str(e), "message": f"更新失败: {str(e)}"}


def delete_csv_file(file_path):
    normalized = _normalize_existing_path(file_path, ".csv")
    if not normalized:
        return {"success": False, "reason": "path_invalid_or_not_found", "message": "路径无效或文件不存在"}
    try:
        os.remove(normalized)
        return {"success": True, "path": normalized, "message": "删除成功"}
    except Exception as e:
        return {"success": False, "reason": "delete_failed", "error": str(e), "message": f"删除失败: {str(e)}"}


def _resolve_parent_path(parent_path):
    if parent_path:
        target_parent = resolve_target_path(parent_path)
    else:
        target_parent = resolve_desktop_path()
    
    if not target_parent or not os.path.exists(target_parent) or not os.path.isdir(target_parent):
        return None
    return os.path.abspath(os.path.normpath(target_parent))


def _ensure_extension(name, extension):
    if name.lower().endswith(extension):
        return name
    return f"{name}{extension}"


def _normalize_existing_path(path, extension):
    if not path:
        return None
    resolved = resolve_target_path(path)
    if not resolved or not os.path.exists(resolved):
        return None
    resolved = os.path.abspath(os.path.normpath(resolved))
    if not resolved.lower().endswith(extension):
        return None
    return resolved


def _read_dataframe(path):
    import pandas as pd
    return pd.read_csv(path)


def _build_dataframe(columns, rows):
    import pandas as pd
    if rows is None:
        rows = []
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list):
        return pd.DataFrame()
    if columns and isinstance(columns, list):
        return pd.DataFrame(rows, columns=columns)
    return pd.DataFrame(rows)


def _concat_dataframes(df, append_df):
    import pandas as pd
    return pd.concat([df, append_df], ignore_index=True)
