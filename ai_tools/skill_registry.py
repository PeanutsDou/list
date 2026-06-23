import sys
import os

# 确保能导入当前目录下的模块
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from ai_tools import ai_task_manager
from ai_tools import ai_split_task
from ai_tools import ai_statistics
from ai_tools import ai_pet_control
from ai_tools import task_hierarchy_manager
from ai_files_tools import ai_files_read
from ai_files_tools import ai_files_getfiles
from ai_files_tools import ai_flies_detailread
from ai_files_tools import ai_files_remove
from ai_files_tools import ai_files_newfile
from ai_files_tools import ai_fles_movefiles
from ai_files_tools import ai_files_deletfiles
from ai_files_tools import ai_files_search
from ai_files_tools import ai_files_markdown
from ai_files_tools import ai_files_doc
from ai_files_tools import ai_files_excel
from ai_files_tools import ai_files_pdf
from ai_files_tools import ai_files_copy
from ai_files_tools import ai_files_open
from ai_files_tools import ai_files_py
from ai_web_tools import ai_web_read
from ai_web_tools import ai_web_open
from ai_web_tools import ai_web_monitorkonwledge
from ai_web_tools import ai_web_read_content
from ai_time_tools import ai_email
from ai_time_tools import ai_money
from ai_soft_tools import ai_soft_open
from ai_soft_tools import ai_soft_read
from ai_soft_tools import ai_soft_monitorkonwledge
from ai_tools import ai_text
from ai_tools import ai_screen
from ai_konwledge.web_konwledge import ai_web
from ai_konwledge.web_konwledge import ai_web_read_info
from ai_konwledge.web_konwledge import ai_web_check
from ai_konwledge.soft_konwledge import ai_soft
from ai_konwledge.soft_konwledge import ai_soft_read_info
from ai_konwledge.soft_konwledge import ai_soft_check
from tools import token_cal
from ai_github_tools import ai_github_repo
from ai_github_tools import ai_github_git

# 定义技能映射（技能名称对应 skills_metadata.json 的 name）
SKILL_MAPPING = {
    # ai_task_manager
    "add_task": ai_task_manager.add_task,
    "add_task_by_date": ai_task_manager.add_task_by_date,
    "add_tasks_batch": ai_task_manager.add_tasks_batch,
    "update_task": ai_task_manager.update_task,
    "update_task_by_date": ai_task_manager.update_task_by_date,
    "update_tasks_batch": ai_task_manager.update_tasks_batch,
    "delete_task": ai_task_manager.delete_task,
    "delete_task_by_date": ai_task_manager.delete_task_by_date,
    "delete_tasks_batch": ai_task_manager.delete_tasks_batch,
    "get_tasks": ai_task_manager.get_task_list,
    "get_tasks_by_date": ai_task_manager.get_tasks_by_date,
    "move_task": ai_task_manager.move_task,
    "move_tasks_batch": ai_task_manager.move_tasks_batch,
    "move_task_by_position": task_hierarchy_manager.move_task_by_position,
    "move_tasks_by_position_batch": task_hierarchy_manager.move_tasks_by_position_batch,
    "clear_history": ai_task_manager.clear_all_history,
    "archive_tasks": ai_task_manager.archive_tasks,
    
    # ai_split_task
    "split_task": ai_split_task.split_task,
    
    # ai_statistics
    "get_statistics": ai_statistics.calculate_history_stats,

    # ai_pet_control
    "get_pet_status": ai_pet_control.get_pet_status,
    "get_pet_features": ai_pet_control.get_pet_features,
    "set_pet_animation": ai_pet_control.set_pet_animation,

    # ai_files_read
    "read_desktop_files": ai_files_read.read_desktop_files,
    "search_desktop_files_by_name": ai_files_search.search_desktop_files_by_name,
    "search_desktop_files_recursive": ai_files_search.search_desktop_files_recursive,

    # ai_files_getfiles
    "add_common_file": ai_files_getfiles.add_common_file,
    "add_common_files_batch": ai_files_getfiles.add_common_files_batch,
    "get_common_files": ai_files_getfiles.get_common_files,
    "record_open_file": ai_files_getfiles.record_open,
    "record_open_files_batch": ai_files_getfiles.record_open_batch,

    # ai_flies_detailread
    "read_path_details": ai_flies_detailread.read_path_details,
    "read_paths_details_batch": ai_flies_detailread.read_paths_details_batch,
    "read_path_details_batch": ai_flies_detailread.read_paths_details_batch,

    # ai_files_remove
    "remove_common_file": ai_files_remove.remove_common_file,
    "remove_common_files_batch": ai_files_remove.remove_common_files_batch,

    # ai_files_newfile
    "create_folder": ai_files_newfile.create_folder,
    "create_folders_batch": ai_files_newfile.create_folders_batch,

    # ai_fles_movefiles
    "move_file": ai_fles_movefiles.move_file,
    "move_files_batch": ai_fles_movefiles.move_files_batch,

    # ai_files_deletfiles
    "delete_file": ai_files_deletfiles.delete_file,
    "delete_files_batch": ai_files_deletfiles.delete_files_batch,

    # ai_files_copy
    "copy_file": ai_files_copy.copy_file,

    # ai_files_open
    "open_file": ai_files_open.open_file,

    # ai_files_markdown
    "create_markdown_file": ai_files_markdown.create_markdown_file,
    "read_markdown_file": ai_files_markdown.read_markdown_file,
    "update_markdown_content": ai_files_markdown.update_markdown_content,
    "append_markdown_content": ai_files_markdown.append_markdown_content,
    "remove_markdown_content": ai_files_markdown.remove_markdown_content,
    "delete_markdown_file": ai_files_markdown.delete_markdown_file,

    # ai_files_doc
    "create_docx_file": ai_files_doc.create_docx_file,
    "read_docx_file": ai_files_doc.read_docx_file,
    "update_docx_content": ai_files_doc.update_docx_content,
    "delete_docx_file": ai_files_doc.delete_docx_file,

    # ai_files_excel
    "create_csv_file": ai_files_excel.create_csv_file,
    "read_csv_file": ai_files_excel.read_csv_file,
    "update_csv_content": ai_files_excel.update_csv_content,
    "delete_csv_file": ai_files_excel.delete_csv_file,

    # ai_files_pdf
    "read_pdf_file": ai_files_pdf.read_pdf_file,
    "delete_pdf_file": ai_files_pdf.delete_pdf_file,

    # ai_files_py
    "create_py_file": ai_files_py.create_py_file,
    "read_py_file": ai_files_py.read_py_file,
    "update_py_content": ai_files_py.update_py_content,
    "delete_py_file": ai_files_py.delete_py_file,

    # token_cal
    "query_token_usage": token_cal.query_usage,

    "list_github_repos": ai_github_repo.list_github_repos,
    "get_github_repo": ai_github_repo.get_github_repo,
    "create_github_repo": ai_github_repo.create_github_repo,
    "delete_github_repo": ai_github_repo.delete_github_repo,
    "update_github_repo": ai_github_repo.update_github_repo,
    "list_github_branches": ai_github_repo.list_github_branches,
    "create_github_branch": ai_github_repo.create_github_branch,
    "delete_github_branch": ai_github_repo.delete_github_branch,
    "list_github_contents": ai_github_repo.list_github_contents,
    "upload_github_file": ai_github_repo.upload_github_file,
    "delete_github_file": ai_github_repo.delete_github_file,
    "create_repo_from_local_path": ai_github_repo.create_repo_from_local_path,
    "git_clone_repo": ai_github_git.git_clone_repo,
    "git_pull_repo": ai_github_git.git_pull_repo,
    "git_checkout_branch": ai_github_git.git_checkout_branch,
    "git_merge_branch": ai_github_git.git_merge_branch,
    "git_push_repo": ai_github_git.git_push_repo,

    # ai_web_read
    "get_all_browsers_info": ai_web_read.get_all_browsers_info,

    # ai_web_open
    "open_url": ai_web_open.open_url,

    # ai_web_monitorkonwledge
    "query_web_knowledge": ai_web_monitorkonwledge.query_web_knowledge,
    "clear_web_knowledge": ai_web_monitorkonwledge.clear_web_knowledge,
    "toggle_web_monitor": ai_web_monitorkonwledge.toggle_web_monitor,
    "read_open_web_content": ai_web_read_content.read_open_web_content,
    "read_web_content_background": ai_web_read_content.read_web_content_background,
    "write_email": ai_email.write_email,
    "send_email": ai_email.send_email,
    "schedule_send_email": ai_email.schedule_send_email,
    "delete_email_task": ai_email.delete_email_task,
    "add_realtime_email_task": ai_email.add_realtime_email_task,
    "get_email_tasks": ai_email.get_email_tasks,
    
    "add_transaction": ai_money.add_transaction,
    "get_transactions": ai_money.get_transactions,
    "get_summary": ai_money.get_summary,

    "get_note": ai_text.get_note,
    "write_note": ai_text.write_note,
    "append_note": ai_text.append_note,
    "update_note": ai_text.update_note,
    "clear_note": ai_text.clear_note,
    "search_note": ai_text.search_note,
    "replace_note_text": ai_text.replace_note_text,
    "remove_note_text": ai_text.remove_note_text,
    "set_note_style_preferences": ai_text.set_note_style_preferences,

    "capture_screen": ai_screen.capture_screen,
    "capture_screen_base64": ai_screen.capture_screen_base64,
    "save_screen_capture": ai_screen.save_screen_capture,
    "list_screen_captures": ai_screen.list_screen_captures,
    "get_latest_screen_capture_path": ai_screen.get_latest_screen_capture_path,
    "read_screen_capture_info": ai_screen.read_screen_capture_info,
    "clear_screen_captures": ai_screen.clear_screen_captures,

    "add_favorite_url": ai_web.add_favorite_url,
    "remove_favorite_url": ai_web.remove_favorite_url,
    "list_favorite_urls": ai_web.list_favorite_urls,
    "search_favorite_urls": ai_web.search_favorite_urls,
    "open_favorite_url": ai_web.open_favorite_url,
    "open_favorite_urls_batch": ai_web.open_favorite_urls_batch,
    "read_web_info": ai_web_read_info.read_web_info,
    "search_web_history_by_keyword": ai_web_check.search_web_history_by_keyword,
    "search_web_history_by_title": ai_web_check.search_web_history_by_title,
    "search_web_history_by_name": ai_web_check.search_web_history_by_name,
    "search_web_history_by_url": ai_web_check.search_web_history_by_url,
    "search_web_history_by_domain": ai_web_check.search_web_history_by_domain,
    "search_web_history_by_browser": ai_web_check.search_web_history_by_browser,
    "search_web_history_by_date": ai_web_check.search_web_history_by_date,
    "search_web_history_by_time_range": ai_web_check.search_web_history_by_time_range,
    "search_web_history_combined": ai_web_check.search_web_history_combined,
    "get_all_apps_info": ai_soft_read.get_all_apps_info,
    "open_app": ai_soft_open.open_app,
    "query_soft_knowledge": ai_soft_monitorkonwledge.query_soft_knowledge,
    "clear_soft_knowledge": ai_soft_monitorkonwledge.clear_soft_knowledge,
    "toggle_soft_monitor": ai_soft_monitorkonwledge.toggle_soft_monitor,
    "add_favorite_app": ai_soft.add_favorite_app,
    "remove_favorite_app": ai_soft.remove_favorite_app,
    "list_favorite_apps": ai_soft.list_favorite_apps,
    "search_favorite_apps": ai_soft.search_favorite_apps,
    "open_favorite_app": ai_soft.open_favorite_app,
    "open_favorite_apps_batch": ai_soft.open_favorite_apps_batch,
    "read_soft_info": ai_soft_read_info.read_soft_info,
    "search_soft_history_by_keyword": ai_soft_check.search_soft_history_by_keyword,
    "search_soft_history_by_title": ai_soft_check.search_soft_history_by_title,
    "search_soft_history_by_name": ai_soft_check.search_soft_history_by_name,
    "search_soft_history_by_app": ai_soft_check.search_soft_history_by_app,
    "search_soft_history_by_process": ai_soft_check.search_soft_history_by_process,
    "search_soft_history_by_exe_path": ai_soft_check.search_soft_history_by_exe_path,
    "search_soft_history_by_date": ai_soft_check.search_soft_history_by_date,
    "search_soft_history_by_time_range": ai_soft_check.search_soft_history_by_time_range,
    "search_soft_history_combined": ai_soft_check.search_soft_history_combined
}

SKILL_PERMISSIONS = {
    "get_tasks": "read",
    "get_tasks_by_date": "read",
    "get_statistics": "read",
    "read_desktop_files": "read",
    "search_desktop_files_by_name": "read",
    "search_desktop_files_recursive": "read",
    "get_common_files": "read",
    "read_path_details": "read",
    "read_path_details_batch": "read",
    "read_paths_details_batch": "read",
    "read_markdown_file": "read",
    "read_docx_file": "read",
    "read_csv_file": "read",
    "read_pdf_file": "read",
    "create_py_file": "write",
    "read_py_file": "read",
    "update_py_content": "write",
    "delete_py_file": "write",
    "query_token_usage": "read",
    "list_github_repos": "read",
    "get_github_repo": "read",
    "list_github_branches": "read",
    "list_github_contents": "read",
    "get_all_browsers_info": "read",
    "query_web_knowledge": "read",
    "get_note": "read",
    "search_note": "read",
    "list_favorite_urls": "read",
    "search_favorite_urls": "read",
    "read_web_info": "read",
    "read_open_web_content": "read",
    "read_web_content_background": "read",
    "get_email_tasks": "read",
    "add_transaction": "write",
    "search_web_history_by_keyword": "read",
    "search_web_history_by_title": "read",
    "search_web_history_by_name": "read",
    "search_web_history_by_url": "read",
    "search_web_history_by_domain": "read",
    "search_web_history_by_browser": "read",
    "search_web_history_by_date": "read",
    "search_web_history_by_time_range": "read",
    "search_web_history_combined": "read",
    "list_screen_captures": "read",
    "get_latest_screen_capture_path": "read",
    "read_screen_capture_info": "read",
    "get_all_apps_info": "read",
    "query_soft_knowledge": "read",
    "list_favorite_apps": "read",
    "search_favorite_apps": "read",
    "read_soft_info": "read",
    "search_soft_history_by_keyword": "read",
    "search_soft_history_by_title": "read",
    "search_soft_history_by_name": "read",
    "search_soft_history_by_app": "read",
    "search_soft_history_by_process": "read",
    "search_soft_history_by_exe_path": "read",
    "search_soft_history_by_date": "read",
    "search_soft_history_by_time_range": "read",
    "search_soft_history_combined": "read"
}

def get_skill_function(skill_name):
    """获取技能对应的函数。"""
    return SKILL_MAPPING.get(skill_name)

def get_all_skills():
    """获取所有技能映射。"""
    return SKILL_MAPPING

def normalize_skill_arguments(skill_name, arguments):
    if not isinstance(arguments, dict):
        return arguments
    if skill_name in {
        "list_github_contents",
        "upload_github_file",
        "delete_github_file",
        "get_github_repo",
        "update_github_repo",
        "delete_github_repo",
        "list_github_branches",
        "create_github_branch",
        "delete_github_branch"
    }:
        normalized = dict(arguments)
        repo_value = normalized.get("repo") or normalized.get("repository") or normalized.get("full_name")
        owner_value = normalized.get("owner") or normalized.get("repo_owner")
        if isinstance(repo_value, str) and "/" in repo_value and not owner_value:
            parts = repo_value.split("/", 1)
            normalized["owner"] = parts[0]
            normalized["repo"] = parts[1]
        if skill_name == "list_github_contents":
            if "path" in normalized and "repo_path" not in normalized:
                normalized["path"] = normalized.get("path", "")
            if "ref" not in normalized:
                normalized["ref"] = ""
        if skill_name == "upload_github_file":
            if "target_path" not in normalized:
                if "path" in normalized:
                    normalized["target_path"] = normalized.get("path")
                elif "repo_path" in normalized:
                    normalized["target_path"] = normalized.get("repo_path")
            if "local_path" not in normalized:
                if "file_path" in normalized:
                    normalized["local_path"] = normalized.get("file_path")
                elif "local" in normalized:
                    normalized["local_path"] = normalized.get("local")
            if "branch" not in normalized:
                normalized["branch"] = ""
        if skill_name == "delete_github_file":
            if "target_path" not in normalized:
                if "path" in normalized:
                    normalized["target_path"] = normalized.get("path")
                elif "repo_path" in normalized:
                    normalized["target_path"] = normalized.get("repo_path")
            if "branch" not in normalized:
                normalized["branch"] = ""
        return normalized
    if skill_name == "create_repo_from_local_path":
        normalized = dict(arguments)
        repo_value = normalized.get("repo_name") or normalized.get("repo") or normalized.get("repository")
        if isinstance(repo_value, str):
            repo_value = repo_value.strip()
            if "/" in repo_value and not normalized.get("owner"):
                parts = repo_value.split("/", 1)
                normalized["owner"] = parts[0]
                normalized["repo_name"] = parts[1]
            else:
                normalized["repo_name"] = repo_value
        if "branch" not in normalized:
            normalized["branch"] = ""
        if "commit_message" not in normalized:
            normalized["commit_message"] = ""
        if "repo_url" not in normalized:
            normalized["repo_url"] = normalized.get("url", "")
        if "use_existing_repo" not in normalized:
            normalized["use_existing_repo"] = True
        if "remote_name" not in normalized:
            normalized["remote_name"] = "origin"
        return normalized
    if skill_name == "read_web_content_background":
        urls_value = arguments.get("urls")
        if urls_value is None:
            for key in ("url", "web_url", "links"):
                if key in arguments:
                    urls_value = arguments.get(key)
                    break
        if urls_value is not None:
            return {
                "urls": urls_value,
                "max_pages": arguments.get("max_pages", 3),
                "max_chars": arguments.get("max_chars", 4000)
            }
    if skill_name in {
        "add_common_files_batch",
        "record_open_files_batch",
        "read_path_details_batch",
        "read_paths_details_batch",
        "remove_common_files_batch",
        "delete_files_batch"
    }:
        paths_list = arguments.get("paths_list")
        if paths_list is None:
            for key in ("paths", "file_paths", "files", "items"):
                if key in arguments:
                    paths_list = arguments.get(key)
                    break
        normalized = _normalize_paths_list(paths_list)
        if normalized is not None:
            return {"paths_list": normalized}
        return arguments
    if skill_name == "move_files_batch":
        moves_list = arguments.get("moves_list")
        if moves_list is None:
            for key in ("moves", "items"):
                if key in arguments:
                    moves_list = arguments.get(key)
                    break
        if moves_list is not None:
            return {"moves_list": moves_list}
        return arguments
    if skill_name == "create_folders_batch":
        folders_list = arguments.get("folders_list")
        if folders_list is None:
            for key in ("folders", "items"):
                if key in arguments:
                    folders_list = arguments.get(key)
                    break
        if folders_list is not None:
            return {"folders_list": folders_list}
        return arguments
    return arguments

def _normalize_paths_list(value):
    if value is None:
        return None
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        items = []
        for item in value:
            if isinstance(item, dict):
                path = item.get("path")
                if path:
                    items.append(path)
            elif isinstance(item, str):
                items.append(item)
        return items
    return None

def get_skill_permission(skill_name):
    permission = SKILL_PERMISSIONS.get(skill_name)
    return permission or "write"
