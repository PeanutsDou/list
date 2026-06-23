import os
import sys
import datetime
import uuid
import json

# 确保能导入 history_data
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from history_data.history_data import load_history, save_history
except ImportError as e:
    print(f"警告：ai_task_manager 无法导入 history_data：{e}")
    def load_history(): return []
    def save_history(data): pass

def _generate_id():
    """生成唯一的任务ID。"""
    return str(uuid.uuid4())[:8]

def _normalize_date(value):
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return None
    return None

def get_task_list(filter_status=None):
    """
    获取任务列表。
    参数：
        filter_status (str, optional): 'pending'、'completed' 或 'all'。
    """
    tasks = load_history()
    # 确保每个任务都有 ID，如果没有则生成并保存
    modified = False
    for t in tasks:
        if 'id' not in t:
            t['id'] = _generate_id()
            modified = True
        if 'children' not in t:
            t['children'] = []
            modified = True
        if 'scheduled_date' not in t or not t.get('scheduled_date'):
            t['scheduled_date'] = datetime.date.today().isoformat()
            modified = True
            
    if modified:
        save_history(tasks)
        
    if filter_status and filter_status != 'all':
        return [t for t in tasks if t.get('status') == filter_status]
    return tasks

def add_task(content, parent_id=None):
    """
    添加任务。
    参数：
        content (str): 任务内容
        parent_id (str, optional): 父任务ID，提供则添加为子任务。
    """
    tasks = load_history()
    now = datetime.datetime.now().isoformat()
    new_task = {
        "id": _generate_id(),
        "content": content,
        "status": "pending",
        "created_at": now,
        "last_updated": now,
        "scheduled_date": datetime.date.today().isoformat(),
        "children": []
    }
    
    if parent_id:
        # 查找父任务并添加
        parent_found = False
        
        # 递归查找父任务的辅助函数
        def find_and_add(task_list):
            nonlocal parent_found
            for t in task_list:
                if t.get('id') == parent_id:
                    if 'children' not in t:
                        t['children'] = []
                    t['children'].append(new_task)
                    parent_found = True
                    return True
                # 递归查找子任务
                if 'children' in t and find_and_add(t['children']):
                    return True
            return False

        find_and_add(tasks)
        
        if not parent_found:
            return {"status": "error", "message": f"未找到父任务 ID：{parent_id}"}
    else:
        tasks.append(new_task)
        
    save_history(tasks)
    return {"status": "success", "message": "任务已添加。", "task": new_task}

def update_task(task_id, content=None, status=None):
    """
    更新任务内容或状态。
    参数：
        task_id (str): 任务ID
        content (str, optional): 新内容
        status (str, optional): 新状态（'pending' 或 'completed'）
    """
    tasks = load_history()
    task_found = None
    now = datetime.datetime.now().isoformat()

    def find_and_update(task_list):
        nonlocal task_found
        for t in task_list:
            if t.get('id') == task_id:
                if content is not None:
                    t['content'] = content
                if status is not None:
                    t['status'] = status
                t['last_updated'] = now
                task_found = t
                return True
            if 'children' in t and find_and_update(t['children']):
                return True
        return False

    if find_and_update(tasks):
        save_history(tasks)
        return {"status": "success", "message": "任务已更新。", "task": task_found}
    else:
        return {"status": "error", "message": f"未找到任务 ID：{task_id}"}

def delete_task(task_id):
    """
    删除任务。
    参数：
        task_id (str): 任务ID
    """
    tasks = load_history()
    deleted = False

    def find_and_delete(task_list):
        nonlocal deleted
        for i, t in enumerate(task_list):
            if t.get('id') == task_id:
                del task_list[i]
                deleted = True
                return True
            if 'children' in t and find_and_delete(t['children']):
                return True
        return False

    if find_and_delete(tasks):
        save_history(tasks)
        return {"status": "success", "message": "任务已删除。"}
    else:
        return {"status": "error", "message": f"未找到任务 ID：{task_id}"}

def add_task_by_date(content, scheduled_date, parent_id=None):
    tasks = load_history()
    now = datetime.datetime.now().isoformat()
    target_date = _normalize_date(scheduled_date) or datetime.date.today()
    new_task = {
        "id": _generate_id(),
        "content": content,
        "status": "pending",
        "created_at": now,
        "last_updated": now,
        "scheduled_date": target_date.isoformat(),
        "children": []
    }

    if parent_id:
        parent_found = False

        def find_and_add(task_list):
            nonlocal parent_found
            for t in task_list:
                if t.get('id') == parent_id:
                    if 'children' not in t:
                        t['children'] = []
                    t['children'].append(new_task)
                    parent_found = True
                    return True
                if 'children' in t and find_and_add(t['children']):
                    return True
            return False

        find_and_add(tasks)

        if not parent_found:
            return {"status": "error", "message": f"未找到父任务 ID：{parent_id}"}
    else:
        tasks.append(new_task)

    save_history(tasks)
    return {"status": "success", "message": "任务已添加。", "task": new_task}

def get_tasks_by_date(scheduled_date, filter_status=None):
    target_date = _normalize_date(scheduled_date)
    if not target_date:
        return []
    tasks = get_task_list(filter_status=filter_status or 'all')
    target_str = target_date.isoformat()

    def filter_recursive(task_list):
        result = []
        for t in task_list:
            task_date = t.get('scheduled_date') or target_str
            if task_date == target_str:
                copied = dict(t)
                if 'children' in t:
                    copied['children'] = filter_recursive(t['children'])
                result.append(copied)
        return result

    return filter_recursive(tasks)

def update_task_by_date(task_id, scheduled_date, content=None, status=None):
    tasks = load_history()
    task_found = None
    now = datetime.datetime.now().isoformat()
    target_date = _normalize_date(scheduled_date)
    if not target_date:
        return {"status": "error", "message": "日期格式不正确"}
    target_str = target_date.isoformat()

    def find_and_update(task_list):
        nonlocal task_found
        for t in task_list:
            if t.get('id') == task_id:
                task_date = t.get('scheduled_date') or target_str
                if task_date != target_str:
                    return False
                if content is not None:
                    t['content'] = content
                if status is not None:
                    t['status'] = status
                t['scheduled_date'] = target_str
                t['last_updated'] = now
                task_found = t
                return True
            if 'children' in t and find_and_update(t['children']):
                return True
        return False

    if find_and_update(tasks):
        save_history(tasks)
        return {"status": "success", "message": "任务已更新。", "task": task_found}
    return {"status": "error", "message": f"未找到指定日期的任务 ID：{task_id}"}

def delete_task_by_date(task_id, scheduled_date):
    tasks = load_history()
    deleted = False
    target_date = _normalize_date(scheduled_date)
    if not target_date:
        return {"status": "error", "message": "日期格式不正确"}
    target_str = target_date.isoformat()

    def find_and_delete(task_list):
        nonlocal deleted
        for i, t in enumerate(task_list):
            if t.get('id') == task_id:
                task_date = t.get('scheduled_date') or target_str
                if task_date != target_str:
                    return False
                del task_list[i]
                deleted = True
                return True
            if 'children' in t and find_and_delete(t['children']):
                return True
        return False

    if find_and_delete(tasks):
        save_history(tasks)
        return {"status": "success", "message": "任务已删除。"}
    return {"status": "error", "message": f"未找到指定日期的任务 ID：{task_id}"}

def delete_tasks_batch(task_ids):
    """
    批量删除任务。
    参数：
        task_ids (list[str]): 任务ID列表
    """
    if not task_ids:
        return {"status": "success", "message": "没有需要删除的任务。"}

    tasks = load_history()
    deleted_count = 0
    not_found_ids = []

    def delete_one_in_memory(current_tasks, target_id):
        for i, t in enumerate(current_tasks):
            if t.get('id') == target_id:
                del current_tasks[i]
                return True
            if 'children' in t and delete_one_in_memory(t['children'], target_id):
                return True
        return False

    for tid in task_ids:
        if delete_one_in_memory(tasks, tid):
            deleted_count += 1
        else:
            not_found_ids.append(tid)

    if deleted_count > 0:
        save_history(tasks)
        
    return {
        "status": "success" if not not_found_ids else "partial_success",
        "message": f"已删除 {deleted_count} 个任务。",
        "not_found": not_found_ids
    }

def update_tasks_batch(updates):
    """
    批量更新任务。
    参数：
        updates (list[dict]): 更新信息列表，每项包含 id/content/status。
    """
    if not updates:
        return {"status": "success", "message": "没有提供更新内容。"}
        
    tasks = load_history()
    updated_count = 0
    now = datetime.datetime.now().isoformat()
    
    # 建立 ID 到 update 信息的映射，方便查找
    update_map = {u.get('id'): u for u in updates if u.get('id')}
    
    def update_recursive(task_list):
        nonlocal updated_count
        for t in task_list:
            tid = t.get('id')
            if tid in update_map:
                u = update_map[tid]
                if 'content' in u and u['content'] is not None:
                    t['content'] = u['content']
                if 'status' in u and u['status'] is not None:
                    t['status'] = u['status']
                t['last_updated'] = now
                updated_count += 1
            
            if 'children' in t:
                update_recursive(t['children'])

    update_recursive(tasks)
    
    if updated_count > 0:
        save_history(tasks)
        
    return {
        "status": "success",
        "message": f"已更新 {updated_count} 个任务。"
    }

def add_tasks_batch(tasks=None, tasks_list=None):
    """
    批量添加任务。
    参数：
        tasks (list[str] or list[dict]): 任务列表
        tasks_list (list[str] or list[dict]): 兼容旧参数的任务列表
    """
    task_items = tasks if tasks is not None else tasks_list
    if not task_items:
        return {"status": "success", "message": "没有需要添加的任务。", "tasks": []}

    tasks = load_history()
    now = datetime.datetime.now().isoformat()
    added_tasks = []
    today_str = datetime.date.today().isoformat()
    
    for item in task_items:
        content = item
        if isinstance(item, dict):
            content = item.get('content', '')
            
        # 批量任务默认绑定到当天日期，确保 UI 可按日渲染
        new_task = {
            "id": _generate_id(),
            "content": content,
            "status": "pending",
            "created_at": now,
            "last_updated": now,
            "scheduled_date": today_str,
            "children": []
        }
        tasks.append(new_task)
        added_tasks.append(new_task)
        
    save_history(tasks)
    return {"status": "success", "message": f"已添加 {len(added_tasks)} 个任务。", "tasks": added_tasks}

def move_task(task_id, new_parent_id=None):
    """
    移动任务（修改父子关系）。
    参数：
        task_id (str): 要移动的任务ID
        new_parent_id (str, optional): 新的父任务ID，None 表示移动到顶层。
    """
    tasks = load_history()
    task_to_move = None

    # 先找到并移除该任务
    def find_and_extract(task_list):
        nonlocal task_to_move
        for i, t in enumerate(task_list):
            if t.get('id') == task_id:
                task_to_move = t
                del task_list[i]
                return True
            if 'children' in t and find_and_extract(t['children']):
                return True
        return False

    if not find_and_extract(tasks):
        return {"status": "error", "message": f"未找到任务 ID：{task_id}"}

    # 插入到新位置
    if new_parent_id:
        parent_found = False
        def find_and_insert(task_list):
            nonlocal parent_found
            for t in task_list:
                if t.get('id') == new_parent_id:
                    if 'children' not in t:
                        t['children'] = []
                    t['children'].append(task_to_move)
                    parent_found = True
                    return True
                if 'children' in t and find_and_insert(t['children']):
                    return True
            return False
            
        find_and_insert(tasks)
        if not parent_found:
            # 如果找不到新父节点，回退操作以防任务丢失
            tasks.append(task_to_move)
            save_history(tasks)
            return {"status": "error", "message": f"未找到新父任务 ID：{new_parent_id}，已移动到顶层。"}
    else:
        # 移动到顶层
        tasks.append(task_to_move)

    save_history(tasks)
    return {"status": "success", "message": "任务已移动。"}

def move_tasks_batch(moves):
    """
    批量移动任务。
    参数：
        moves (list[dict]): 每项包含 task_id/new_parent_id。
    """
    if not moves:
        return {"status": "success", "message": "没有需要移动的任务。", "moved": 0}

    tasks = load_history()
    moved_count = 0
    not_found_tasks = []
    not_found_parents = []
    invalid_items = []

    def find_and_extract(task_list, target_id):
        for i, t in enumerate(task_list):
            if t.get('id') == target_id:
                return task_list.pop(i)
            if 'children' in t:
                found = find_and_extract(t['children'], target_id)
                if found:
                    return found
        return None

    def find_task(task_list, target_id):
        for t in task_list:
            if t.get('id') == target_id:
                return t
            if 'children' in t:
                found = find_task(t['children'], target_id)
                if found:
                    return found
        return None

    for move in moves:
        if not isinstance(move, dict):
            invalid_items.append(move)
            continue
        task_id = move.get('task_id') or move.get('id')
        new_parent_id = move.get('new_parent_id')
        if not task_id:
            invalid_items.append(move)
            continue
        task_to_move = find_and_extract(tasks, task_id)
        if not task_to_move:
            not_found_tasks.append(task_id)
            continue
        if new_parent_id:
            parent_task = find_task(tasks, new_parent_id)
            if not parent_task:
                tasks.append(task_to_move)
                not_found_parents.append(new_parent_id)
                continue
            if 'children' not in parent_task or parent_task['children'] is None:
                parent_task['children'] = []
            parent_task['children'].append(task_to_move)
        else:
            tasks.append(task_to_move)
        moved_count += 1

    if moved_count > 0:
        save_history(tasks)

    status = "success" if not not_found_tasks and not not_found_parents and not invalid_items else "partial_success"
    return {
        "status": status,
        "message": f"已移动 {moved_count} 个任务。",
        "moved": moved_count,
        "not_found_tasks": not_found_tasks,
        "not_found_parents": not_found_parents,
        "invalid_items": invalid_items
    }

def save_ui_pending_tasks(ui_task_list, current_date=None):
    """
    保存来自 UI 的任务列表（包含已完成与未完成），并保留其他日期的数据。
    这个函数专门用于 ui_labels.py 的整体保存逻辑，替代 UI 层的数据处理。
    
    参数：
        ui_task_list (list[dict]): 来自 UI 的任务数据列表。
    """
    # 1. 读取现有所有数据
    current_data = load_history()
    
    def normalize_date(value):
        if isinstance(value, datetime.date):
            return value
        if isinstance(value, str):
            try:
                return datetime.date.fromisoformat(value)
            except ValueError:
                return None
        return None

    normalized_current_date = normalize_date(current_date)

    # 2. 保留非当前日期的数据，当前日期以 UI 结果为准
    preserved_tasks = []
    if normalized_current_date:
        for t in current_data:
            task_date = normalize_date(t.get('scheduled_date'))
            task_date = task_date or normalized_current_date
            if task_date != normalized_current_date:
                preserved_tasks.append(t)
    
    # 3. 构建新的任务列表（包含已完成与未完成）
    new_tasks = []
    now = datetime.datetime.now().isoformat()
    default_scheduled_date = normalized_current_date.isoformat() if normalized_current_date else datetime.date.today().isoformat()
    
    for task_data in ui_task_list:
        # 如果 UI 传来的数据里没有 ID，则生成一个
        task_entry = {
            "id": task_data.get('id', _generate_id()), # 尝试获取 ID，如果没有则生成
            "content": task_data.get('content', ''),
            "status": task_data.get('status', 'pending'),
            "created_at": task_data.get('created_at', now),
            "last_updated": now,
            "scheduled_date": task_data.get('scheduled_date') or default_scheduled_date,
            "children": task_data.get('children', [])
        }
        new_tasks.append(task_entry)
        
    # 4. 合并并保存
    full_data = preserved_tasks + new_tasks
    save_history(full_data)
    
    return {"status": "success", "message": "任务已保存。"}

def clear_all_history():
    """清空所有历史数据。"""
    save_history([])
    return {"status": "success", "message": "历史数据已清空。"}

def archive_tasks(tasks_data):
    """
    归档任务列表。
    参数：
        tasks_data (list[dict]): 需要归档的任务数据列表
    """
    if not tasks_data:
        return {"status": "success", "message": "没有需要归档的任务。"}
        
    history = load_history()
    history.extend(tasks_data)
    save_history(history)
    return {"status": "success", "message": f"已归档 {len(tasks_data)} 个任务。"}
