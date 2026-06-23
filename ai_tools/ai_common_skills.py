import sys
import os

# 确保能导入项目根目录
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

# ai_common_skills.py 曾作为主要的任务管理工具
# 现在这些功能已经迁移到 ai_task_manager.py
# 为了保持兼容性，我们从新模块导入这些函数
# 建议后续代码直接使用 ai_task_manager

from ai_tools.ai_task_manager import (
    get_task_list,
    add_task,
    update_task,
    delete_task,
    delete_tasks_batch,
    update_tasks_batch,
    add_tasks_batch,
    move_task
)

# 如果有其他通用的 AI 技能函数，可以在这里继续添加
# 目前保持精简，只作为兼容层或存放真正通用的“技能”
