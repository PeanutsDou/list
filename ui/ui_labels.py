import json
import os
import sys
import datetime

# 确保能导入 ai_tools
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入 AI 业务逻辑模块
try:
    from ai_tools import ai_task_manager
    from ai_tools.ai_split_task import split_task
    from ai_tools.task_hierarchy_manager import save_ui_tasks, generate_task_id
except ImportError:
    print("警告：无法导入 ai_tools 模块")
    # 简单兜底，防止程序直接崩溃，但业务功能会失效
    class MockTaskManager:
        def get_task_list(self, filter_status=None): return []
        def save_ui_pending_tasks(self, data): pass
    ai_task_manager = MockTaskManager()
    def split_task(content): return [content]
    def save_ui_tasks(data, current_date=None): return None
    def generate_task_id(): return ""

# 导入新的 TaskWidget 和 AutoResizingTextEdit（来自 ui_labels_time）
try:
    from ui.ui_labels_time import TaskWidget, AutoResizingTextEdit, check_and_archive_tasks
except ImportError:
    # 如果作为脚本直接运行
    from ui_labels_time import TaskWidget, AutoResizingTextEdit, check_and_archive_tasks

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QScrollArea, QTextEdit, QFrame, QSizePolicy, QApplication, QLabel)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QPalette

# 同步管理器用于避免 AI 操作与 UI 冲突
try:
    from core.sync_manager import get_sync_manager
except Exception:
    class _FallbackSyncManager:
        """
        同步管理器的降级实现，保持 UI 逻辑可运行。
        """
        def is_ai_processing(self):
            """
            返回 AI 是否正在处理的标记，降级为始终不处理。
            """
            return False

    _fallback_sync_manager = _FallbackSyncManager()

    def get_sync_manager():
        """
        获取降级同步管理器实例。
        """
        return _fallback_sync_manager

class TaskListManager(QWidget):
    """
    任务清单管理组件
    """
    def __init__(self, parent=None):
        """初始化任务清单管理器并加载数据。"""
        super().__init__(parent)
        
        # 样式参数
        self.current_text_color = "white"
        self.current_border_color = "rgba(255, 255, 255, 50)"
        self.current_bg_color = "rgba(0, 0, 0, 50)"
        self.is_light_theme = False
        
        # 选中项管理
        self.selected_task = None
        self.sync_manager = get_sync_manager()

        self.current_date = datetime.date.today()
        
        self.init_ui()

        # 加载任务
        self.load_tasks_from_file()

        # 定时刷新任务 (每 2 秒检查一次文件变动)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.check_and_reload)
        self.refresh_timer.start(2000)
        self.last_load_time = 0

        # 定时检查历史归档 (每分钟检查一次)
        self.archive_timer = QTimer(self)
        self.archive_timer.timeout.connect(self.run_archive_check)
        self.archive_timer.start(60000) 

    def init_ui(self):
        """初始化界面布局与控件。"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 顶部控制栏
        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)
        
        self.add_btn = QPushButton("＋")
        self.del_btn = QPushButton("－")
        self.completed_btn = QPushButton("Done")
        self.ai_btn = QPushButton("AITASK")
        self.prev_date_btn = QPushButton("<")
        self.date_label = QLabel("")
        self.next_date_btn = QPushButton(">")
        
        # 扩大按钮尺寸
        for btn in (self.add_btn, self.del_btn, self.completed_btn, self.ai_btn, self.prev_date_btn, self.next_date_btn):
            if btn == self.ai_btn:
                btn.setFixedSize(80, 30)
            elif btn == self.completed_btn:
                btn.setFixedSize(60, 30)
            else:
                btn.setFixedSize(30, 30)
                
            btn.setCursor(Qt.PointingHandCursor)
            # 初始样式
            btn.setStyleSheet("""
                QPushButton {
                    border: none; 
                    font-weight: bold; 
                    font-size: 16px; 
                    background-color: transparent;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 30);
                }
            """)

        self.add_btn.clicked.connect(self.add_task)
        self.del_btn.clicked.connect(self.remove_task)
        self.completed_btn.clicked.connect(self.mark_completed)
        self.ai_btn.clicked.connect(self.ai_split_current_task)
        self.prev_date_btn.clicked.connect(self.go_previous_day)
        self.next_date_btn.clicked.connect(self.go_next_day)
        
        control_layout.addWidget(self.add_btn)
        control_layout.addWidget(self.del_btn)
        control_layout.addWidget(self.completed_btn)
        control_layout.addWidget(self.ai_btn)
        control_layout.addWidget(self.prev_date_btn)
        control_layout.addWidget(self.date_label)
        control_layout.addWidget(self.next_date_btn)
        control_layout.addStretch() 
        
        layout.addLayout(control_layout)
        self.update_date_label()

        # 2. 滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setWidgetResizable(True)
        
        # 显式设置背景透明
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        self.scroll_area.viewport().setStyleSheet("background: transparent;")
        
        self.task_container = QWidget()
        self.task_container.setAttribute(Qt.WA_TranslucentBackground) # 关键：设置容器透明
        self.task_container.setStyleSheet("background: transparent;")
        
        self.task_layout = QVBoxLayout(self.task_container)
        self.task_layout.setContentsMargins(10, 5, 5, 5)
        self.task_layout.setSpacing(8)
        self.task_layout.addStretch() 
        
        self.scroll_area.setWidget(self.task_container)
        layout.addWidget(self.scroll_area)

    def normalize_date(self, value):
        if isinstance(value, datetime.date):
            return value
        if isinstance(value, str):
            try:
                return datetime.date.fromisoformat(value)
            except ValueError:
                return None
        return None

    def set_current_date(self, date_value):
        normalized = self.normalize_date(date_value)
        if not normalized:
            return
        if normalized == self.current_date:
            return
        self.save_tasks_to_file()
        self.current_date = normalized
        self.update_date_label()
        self.load_tasks_from_file()

    def update_date_label(self):
        if not hasattr(self, "date_label"):
            return
        # 显示日期和星期 之前 进行星期几的中文转译
        week_dict = {
            "Monday": "周一",
            "Tuesday": "周二",
            "Wednesday": "周三",
            "Thursday": "周四",
            "Friday": "周五",
            "Saturday": "周六",
            "Sunday": "周日"
        }
        self.date_label.setText(self.current_date.strftime("%Y-%m-%d %A").replace(self.current_date.strftime("%A"), week_dict[self.current_date.strftime("%A")]))

    def shift_current_date(self, days):
        target_date = self.current_date + datetime.timedelta(days=days)
        self.set_current_date(target_date)

    def go_previous_day(self):
        self.shift_current_date(-1)

    def go_next_day(self):
        self.shift_current_date(1)

    def load_tasks_from_file(self):
        """从 ai_task_manager 加载当天任务（包含已完成与未完成）。"""
        # 获取全部任务数据，避免已完成任务在界面中消失
        all_tasks = ai_task_manager.get_task_list(filter_status='all')
        
        # 安全重置选中状态，防止访问已销毁的对象
        self.selected_task = None

        # 清空当前显示（保留最后的 stretch）
        while self.task_layout.count() > 1:
            item = self.task_layout.itemAt(0)
            if item.widget():
                item.widget().deleteLater()
            self.task_layout.removeItem(item)
            
        # 只展示当前日期的任务
        for task_data in all_tasks:
            task_date = self.normalize_date(task_data.get('scheduled_date'))
            if not task_date:
                task_date = self.current_date
            if task_date != self.current_date:
                continue
            task_widget = self.build_task_widget_from_data(task_data)
            if not task_widget:
                continue
            count = self.task_layout.count()
            self.task_layout.insertWidget(count - 1, task_widget)
            self.apply_task_style(task_widget)

        # 主动刷新布局与滚动区域，确保 UI 立即可见
        self.task_container.adjustSize()
        self.task_container.update()
        self.scroll_area.viewport().update()

        self.last_load_time = os.path.getmtime(os.path.join(project_root, "history_data/history_data.json")) if os.path.exists(os.path.join(project_root, "history_data/history_data.json")) else 0

    def save_tasks_to_file(self):
        """将当前 UI 中的任务树保存到数据文件。"""
        if self.sync_manager.is_ai_processing():
            return
        top_level_tasks = self.get_top_level_tasks()
        save_ui_tasks(top_level_tasks, current_date=self.current_date)
        
        # 更新 last_load_time
        history_path = os.path.join(project_root, "history_data/history_data.json")
        if os.path.exists(history_path):
             self.last_load_time = os.path.getmtime(history_path)

    def check_and_reload(self):
        """检查文件是否被外部修改并刷新显示。"""
        history_path = os.path.join(project_root, "history_data/history_data.json")
        if not os.path.exists(history_path):
            return
            
        mtime = os.path.getmtime(history_path)
        if mtime > self.last_load_time:
            # 文件有变动，重新加载
            try:
                # 只有当选中任务处于编辑模式时才跳过重载，避免打断用户输入
                if self.selected_task and not self.selected_task.text_edit.isReadOnly():
                    return
            except RuntimeError:
                # 如果 selected_task 已经销毁，视为没有选中，继续重载
                self.selected_task = None
            except Exception:
                self.selected_task = None
            
            # 否则（未选中，或选中但只是查看），都进行重载
            self.load_tasks_from_file()

    def add_task(self):
        """添加一个新的任务框。"""
        if self.sync_manager.is_ai_processing():
            return
        task_widget = TaskWidget()
        task_widget.task_id = generate_task_id()
        task_widget.scheduled_date = self.current_date
        # 连接选中信号
        self.bind_task_widget_signals(task_widget)
        
        # 监听文本变化以自动保存
        task_widget.text_edit.focusOutEvent = self.create_focus_out_handler(task_widget.text_edit)
        
        self.apply_task_style(task_widget)
        
        count = self.task_layout.count()
        self.task_layout.insertWidget(count - 1, task_widget)
        
        # 新建任务时，自动进入编辑模式并选中
        task_widget.text_edit.setReadOnly(False)
        task_widget.text_edit.setFocus()
        self.handle_task_selection(task_widget)
        
        QApplication.processEvents()
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )
        # 添加后立即保存（生成空条目）
        self.save_tasks_to_file()

    def create_focus_out_handler(self, text_edit):
        """生成失焦保存的事件包装器。"""
        original_focus_out = text_edit.focusOutEvent
        def new_focus_out(event):
            original_focus_out(event)
            if self.sync_manager.is_ai_processing():
                return
            self.save_tasks_to_file()
        return new_focus_out

    def handle_task_selection(self, task_widget):
        """处理任务选中逻辑。"""
        # 如果点击的是已选中的，不做处理
        if self.selected_task == task_widget:
            return

        # 取消之前的选中状态
        if self.selected_task:
            try:
                self.selected_task.is_selected = False
                self.apply_task_style(self.selected_task)
            except RuntimeError:
            # 如果之前的对象已被销毁，忽略错误
                pass
            # 选中切换时保存
            self.save_tasks_to_file()

        # 设置新的选中状态
        self.selected_task = task_widget
        try:
            self.selected_task.is_selected = True
            self.apply_task_style(self.selected_task)
        except RuntimeError:
            self.selected_task = None

    def insert_task_at(self, index, text=""):
        """在指定位置插入任务。"""
        if self.sync_manager.is_ai_processing():
            return None
        # 这个方法主要用于 AI 拆分后插入子任务，但现在改为直接添加到子任务列表
        # 如果仍然需要在顶层插入任务，保留此方法
        task_widget = TaskWidget(text)
        task_widget.task_id = generate_task_id()
        task_widget.scheduled_date = self.current_date
        self.bind_task_widget_signals(task_widget)
        self.apply_task_style(task_widget)
        
        self.task_layout.insertWidget(index, task_widget)
        self.save_tasks_to_file()
        return task_widget

    def ai_split_current_task(self):
        """AI 拆分当前选中任务。"""
        if not self.selected_task:
            return
            
        content = self.selected_task.text_edit.toPlainText().strip()
        if not content:
            return
            
        self.ai_btn.setEnabled(False)
        self.ai_btn.setText("AIing...")
        QApplication.processEvents()
        
        try:
            subtasks = split_task(content)
            
            if subtasks:
                # 现在的逻辑：不删除当前任务，而是将结果作为子任务添加
                for task_str in subtasks:
                    new_sub_task = TaskWidget(task_str)
                    new_sub_task.task_id = generate_task_id()
                    self.bind_task_widget_signals(new_sub_task)
                    self.apply_task_style(new_sub_task)
                    self.selected_task.add_subtask(new_sub_task)
                self.selected_task.structure_changed.emit()
                
                self.save_tasks_to_file()
                    
        except Exception as e:
            print(f"AI 拆分失败：{e}")
        finally:
            self.ai_btn.setEnabled(True)
            self.ai_btn.setText("AITASK")

    def remove_task(self):
        """
        移除任务：
        1. 如果有选中的任务，删除选中的任务。
        2. 如果没有选中的任务，删除最后一个任务。
        """
        if self.sync_manager.is_ai_processing():
            return
        if self.selected_task:
            # 检查是否有父任务
            if self.selected_task.parent_task:
                self.selected_task.parent_task.remove_subtask(self.selected_task)
            else:
                self.selected_task.deleteLater()
            self.selected_task = None
        else:
            # 删除最后一个 (count > 1 因为有个 stretch)
            count = self.task_layout.count()
            if count > 1:
                item = self.task_layout.itemAt(count - 2)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        
        self.save_tasks_to_file()

    def mark_completed(self):
        """将当前选中任务标记为完成。"""
        if self.sync_manager.is_ai_processing():
            return
        if self.selected_task:
            self.selected_task.set_completed()
            # 标记完成后，立即触发一次归档检查（将已完成的任务存入历史）
            self.run_archive_check()
            self.save_tasks_to_file()

    def get_all_tasks(self):
        """获取所有顶层任务控件列表。"""
        tasks = []
        for i in range(self.task_layout.count()):
            item = self.task_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), TaskWidget):
                tasks.append(item.widget())
        return tasks

    def run_archive_check(self):
        """运行历史归档检查。"""
        tasks = self.get_all_tasks()
        check_and_archive_tasks(tasks)
        # 归档可能修改了任务列表，需同步保存
        self.save_tasks_to_file()

    def update_style(self, text_color, border_color, is_light_theme):
        """更新组件样式。"""
        self.current_text_color = text_color
        self.current_border_color = border_color
        self.is_light_theme = is_light_theme
        
        # 按钮样式
        btn_hover_bg = "rgba(0, 0, 0, 20)" if is_light_theme else "rgba(255, 255, 255, 20)"
        btn_pressed_color = "white" if is_light_theme else "black"
        
        # 扩大按钮尺寸后的样式
        btn_style = f"""
            QPushButton {{
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 15px; /* 圆角适配 */
                background-color: transparent;
                font-family: "Microsoft YaHei";
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {btn_hover_bg};
            }}
            QPushButton:pressed {{
                background-color: {border_color};
                color: {btn_pressed_color};
            }}
        """
        self.add_btn.setStyleSheet(btn_style)
        self.del_btn.setStyleSheet(btn_style)
        self.completed_btn.setStyleSheet(btn_style)
        self.prev_date_btn.setStyleSheet(btn_style)
        self.next_date_btn.setStyleSheet(btn_style)
        
        # AITASK 按钮样式（适当调小字体以适配宽度）
        ai_btn_style = btn_style.replace("font-size: 16px;", "font-size: 14px;")
        self.ai_btn.setStyleSheet(ai_btn_style)
        self.date_label.setStyleSheet(f"color: {text_color}; font-weight: bold;")

        # 滚动条样式
        scrollbar_bg = "transparent"
        handle_color = "rgba(0, 0, 0, 50)" if is_light_theme else "rgba(255, 255, 255, 50)"
        handle_hover = "rgba(0, 0, 0, 100)" if is_light_theme else "rgba(255, 255, 255, 100)"
        
        # 确保滚动区域及其视口背景透明
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            /* Viewport (滚动内容区域) 必须透明 */
            QScrollArea > QWidget > QWidget {{
                background: transparent;
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {scrollbar_bg};
                width: 6px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {handle_color};
                min-height: 20px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {handle_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        
        # 再次强制 viewport 透明
        self.scroll_area.viewport().setStyleSheet("background: transparent;")

        # 更新所有任务框样式
        # 计算背景色
        self.current_bg_color = "rgba(0, 0, 0, 20)" if is_light_theme else "rgba(255, 255, 255, 20)"
        
        for i in range(self.task_layout.count() - 1):
            item = self.task_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, TaskWidget):
                self.apply_task_style(widget)

    def build_task_widget_from_data(self, task_data):
        """从任务数据构建任务控件及其子树。"""
        content = task_data.get('content', '')
        if not content:
            return None

        task_widget = TaskWidget(content)
        task_widget.task_id = task_data.get('id') or generate_task_id()
        task_widget.is_completed = task_data.get('status') == 'completed'
        task_date = self.normalize_date(task_data.get('scheduled_date')) or self.current_date
        task_widget.scheduled_date = task_date

        created_at = task_data.get('created_at')
        updated_at = task_data.get('last_updated') or task_data.get('updated_time')
        if created_at:
            try:
                task_widget.created_time = datetime.datetime.fromisoformat(created_at)
            except ValueError:
                task_widget.created_time = datetime.datetime.now()
        if updated_at:
            try:
                task_widget.updated_time = datetime.datetime.fromisoformat(updated_at)
            except ValueError:
                task_widget.updated_time = datetime.datetime.now()
        task_widget.update_time_label()

        if task_widget.is_completed:
            task_widget.set_completed()

        self.bind_task_widget_signals(task_widget)

        children = task_data.get('children', [])
        if children:
            for child_data in children:
                child_widget = self.build_task_widget_from_data(child_data)
                if child_widget:
                    task_widget.add_subtask(child_widget)

        return task_widget

    def bind_task_widget_signals(self, task_widget):
        """绑定任务控件的选中与结构变更信号。"""
        task_widget.selected.connect(self.handle_task_selection)
        task_widget.subtask_added.connect(self.on_subtask_added)
        task_widget.structure_changed.connect(self.save_tasks_to_file)

        task_widget.text_edit.focusOutEvent = self.create_focus_out_handler(task_widget.text_edit)

    def on_subtask_added(self, sub_task_widget):
        """接收子任务新增信号并绑定样式与保存。"""
        if self.sync_manager.is_ai_processing():
            return
        self.bind_task_widget_signals(sub_task_widget)
        self.apply_task_style(sub_task_widget)
        self.save_tasks_to_file()

    def get_top_level_tasks(self):
        """获取当前顶层任务控件列表。"""
        tasks = []
        for i in range(self.task_layout.count() - 1):
            item = self.task_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, TaskWidget):
                tasks.append(widget)
        return tasks

    def apply_task_style(self, widget):
        """应用样式到单个任务框"""
        widget.set_style(
            self.current_text_color,
            self.current_border_color,
            self.current_bg_color,
            self.is_light_theme
        )
