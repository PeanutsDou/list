import os
import sys
import datetime
from datetime import timedelta

# 确保能导入 history_data
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from history_data.history_data import load_history
except ImportError as e:
    print(f"警告：ai_statistics 无法导入 history_data：{e}")
    def load_history(): return []

def calculate_history_stats():
    """
    计算历史任务统计数据
    
    Returns:
        dict: 包含以下字段的统计数据:
            - total_completed: 总已完成数
            - total_uncompleted: 总未完成数
            - yesterday_completed: 昨日已完成数
            - yesterday_uncompleted: 昨日未完成数
    """
    data = load_history()
    
    stats = {
        "total_completed": 0,
        "total_uncompleted": 0,
        "yesterday_completed": 0,
        "yesterday_uncompleted": 0
    }
    
    now = datetime.datetime.now()
    yesterday = (now - timedelta(days=1)).date()
    
    def update_stats(task_list):
        for task in task_list:
            status = task.get("status", "")
            last_updated_str = task.get("last_updated", "")

            task_date = None
            if last_updated_str:
                try:
                    last_updated = datetime.datetime.fromisoformat(last_updated_str)
                    task_date = last_updated.date()
                except ValueError:
                    task_date = None

            if status == "completed":
                stats["total_completed"] += 1
                if task_date == yesterday:
                    stats["yesterday_completed"] += 1
            else:
                stats["total_uncompleted"] += 1
                if task_date == yesterday:
                    stats["yesterday_uncompleted"] += 1

            children = task.get("children") or []
            if children:
                update_stats(children)

    update_stats(data)
                
    return stats
