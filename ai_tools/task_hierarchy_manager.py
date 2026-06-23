"""
任务层级与拖拽排序的通用管理模块。
该模块同时提供：
1) 基于任务ID的父子移动与排序更新（供 AI 技能调用）。
2) 基于 UI 任务控件树的序列化与保存（供 UI 使用）。
"""

import os
import sys
import datetime
import uuid

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from history_data.history_data import load_history, save_history
from ai_tools import ai_task_manager


def generate_task_id():
    """生成新的任务ID。"""
    return str(uuid.uuid4())[:8]


def _ensure_task_fields(task):
    """补全任务字段，保证结构可用。"""
    now = datetime.datetime.now().isoformat()
    if "id" not in task or not task["id"]:
        task["id"] = generate_task_id()
    if "children" not in task or task["children"] is None:
        task["children"] = []
    if "created_at" not in task:
        task["created_at"] = now
    if "last_updated" not in task:
        task["last_updated"] = now
    if "status" not in task:
        task["status"] = "pending"


def _normalize_task_tree(tasks):
    """递归标准化任务树，确保每个节点结构一致。"""
    for task in tasks:
        _ensure_task_fields(task)
        if task.get("children"):
            _normalize_task_tree(task["children"])


def _find_task_and_parent(task_list, task_id):
    """递归查找任务及其父列表与索引。"""
    for index, task in enumerate(task_list):
        if task.get("id") == task_id:
            return task, task_list, index
        children = task.get("children", [])
        if children:
            found = _find_task_and_parent(children, task_id)
            if found:
                return found
    return None


def _is_descendant(node, target_id):
    """判断目标ID是否为当前节点的子孙节点。"""
    for child in node.get("children", []):
        if child.get("id") == target_id:
            return True
        if _is_descendant(child, target_id):
            return True
    return False


def _move_task_by_position_in_memory(tasks, task_id, target_id, position):
    if task_id == target_id:
        return {"status": "error", "message": "任务不能移动到自身。"}

    source_found = _find_task_and_parent(tasks, task_id)
    target_found = _find_task_and_parent(tasks, target_id)
    if not source_found or not target_found:
        return {"status": "error", "message": "未找到任务或目标任务。"}

    source_task, source_list, source_index = source_found
    target_task, target_list, target_index = target_found

    if _is_descendant(source_task, target_id):
        return {"status": "error", "message": "不能将任务移动到自己的子任务中。"}

    source_list.pop(source_index)

    if position == "child":
        if "children" not in target_task or target_task["children"] is None:
            target_task["children"] = []
        target_task["children"].append(source_task)
    elif position == "before":
        target_list.insert(target_index, source_task)
    elif position == "after":
        target_list.insert(target_index + 1, source_task)
    else:
        return {"status": "error", "message": "不支持的移动位置。"}

    return {"status": "success", "message": "任务移动成功。"}


def move_task_by_position(task_id, target_id, position):
    """
    按拖拽位置移动任务。
    position 取值："before" | "after" | "child"
    """
    tasks = load_history()
    _normalize_task_tree(tasks)
    result = _move_task_by_position_in_memory(tasks, task_id, target_id, position)
    if result.get("status") == "success":
        save_history(tasks)
    return result


def move_tasks_by_position_batch(moves):
    """
    批量按拖拽位置移动任务。
    参数：
        moves (list[dict]): 每项包含 task_id/target_id/position。
    """
    if not moves:
        return {"status": "success", "message": "没有需要移动的任务。", "moved": 0}

    tasks = load_history()
    _normalize_task_tree(tasks)

    moved_count = 0
    errors = []

    for move in moves:
        if not isinstance(move, dict):
            errors.append({"item": move, "message": "参数格式不正确。"})
            continue
        task_id = move.get("task_id")
        target_id = move.get("target_id")
        position = move.get("position")
        if not task_id or not target_id or not position:
            errors.append({"item": move, "message": "参数缺失。"})
            continue
        result = _move_task_by_position_in_memory(tasks, task_id, target_id, position)
        if result.get("status") == "success":
            moved_count += 1
        else:
            errors.append({"item": move, "message": result.get("message")})

    if moved_count > 0:
        save_history(tasks)

    status = "success" if not errors else "partial_success"
    return {"status": status, "message": f"已移动 {moved_count} 个任务。", "moved": moved_count, "errors": errors}


def move_task_to_parent(task_id, new_parent_id=None, new_index=None):
    """按父级与索引移动任务，用于纯数据层的重排。"""
    tasks = load_history()
    _normalize_task_tree(tasks)

    source_found = _find_task_and_parent(tasks, task_id)
    if not source_found:
        return {"status": "error", "message": "未找到目标任务。"}

    source_task, source_list, source_index = source_found
    source_list.pop(source_index)

    if new_parent_id:
        parent_found = _find_task_and_parent(tasks, new_parent_id)
        if not parent_found:
            return {"status": "error", "message": "未找到新的父任务。"}
        parent_task, _, _ = parent_found
        if _is_descendant(source_task, new_parent_id):
            return {"status": "error", "message": "不能将任务移动到自己的子任务中。"}
        if "children" not in parent_task or parent_task["children"] is None:
            parent_task["children"] = []
        target_list = parent_task["children"]
    else:
        target_list = tasks

    if new_index is None or new_index < 0 or new_index > len(target_list):
        target_list.append(source_task)
    else:
        target_list.insert(new_index, source_task)

    save_history(tasks)
    return {"status": "success", "message": "任务已移动到指定父级。"}


def build_task_tree_from_widgets(task_widgets):
    """根据 UI 任务控件构建可保存的任务树结构。"""
    now = datetime.datetime.now().isoformat()
    result = []

    for widget in task_widgets:
        task_id = getattr(widget, "task_id", None) or generate_task_id()
        widget.task_id = task_id

        created_time = getattr(widget, "created_time", None)
        updated_time = getattr(widget, "updated_time", None)

        task_entry = {
            "id": task_id,
            "content": widget.text_edit.toPlainText().strip(),
            "status": "completed" if getattr(widget, "is_completed", False) else "pending",
            "created_at": created_time.isoformat() if created_time else now,
            "last_updated": updated_time.isoformat() if updated_time else now,
            "scheduled_date": getattr(widget, "scheduled_date", None).isoformat() if getattr(widget, "scheduled_date", None) else None,
            "children": []
        }

        sub_widgets = getattr(widget, "subtasks", [])
        if sub_widgets:
            task_entry["children"] = build_task_tree_from_widgets(sub_widgets)

        result.append(task_entry)

    return result


def save_ui_tasks(task_widgets, current_date=None):
    """将 UI 任务控件树保存到历史数据。"""
    task_tree = build_task_tree_from_widgets(task_widgets)
    return ai_task_manager.save_ui_pending_tasks(task_tree, current_date=current_date)
