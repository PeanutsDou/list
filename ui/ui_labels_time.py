from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTextEdit, QFrame, QSizePolicy, QApplication, QLabel)
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData, QPoint, QTimer
from PyQt5.QtGui import QDrag, QPixmap, QPainter, QColor, QFont, QTextCharFormat, QTextCursor
import datetime
import sys
import os

# 导入任务管理与层级处理模块
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from ai_tools import ai_task_manager
    from ai_tools.task_hierarchy_manager import generate_task_id
except ImportError:
    print("警告：ui_labels_time 无法导入 ai_task_manager")
    ai_task_manager = None
    def generate_task_id():
        return ""

class AutoResizingTextEdit(QTextEdit):
    """
    自动调整高度的文本输入框
    支持点击选中，双击编辑
    """
    clicked = pyqtSignal(object)

    def __init__(self, parent=None):
        """初始化文本输入框并绑定事件。"""
        super().__init__(parent)
        self.setAcceptRichText(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.textChanged.connect(self.adjust_height)
        self.setPlaceholderText("输入任务内容...")
        
        # 默认只读，用于实现"双击编辑"
        self.setReadOnly(True)
        self.viewport().setCursor(Qt.ArrowCursor)
        self.is_selected = False
        self.drag_start_pos = None
        
        # 初始高度调整
        self.adjust_height()

    def adjust_height(self):
        """根据内容调整高度。"""
        document = self.document()
        document.setTextWidth(self.viewport().width())
        height = document.size().height()
        
        margins = self.contentsMargins()
        total_height = height + margins.top() + margins.bottom() + 10
        
        self.setFixedHeight(int(max(40, total_height)))

    def resizeEvent(self, event):
        """窗口尺寸变化时同步高度。"""
        super().resizeEvent(event)
        self.adjust_height()

    def mousePressEvent(self, event):
        """只读状态下记录拖拽起点并触发选中。"""
        if self.isReadOnly():
            if event.button() == Qt.LeftButton:
                self.drag_start_pos = event.pos()
                self.clicked.emit(self)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """在只读模式下支持拖拽启动。"""
        if self.isReadOnly():
            if event.buttons() & Qt.LeftButton and self.drag_start_pos:
                if (event.pos() - self.drag_start_pos).manhattanLength() > QApplication.startDragDistance():
                    parent = self.parent()
                    while parent:
                        if hasattr(parent, 'start_drag'):
                            parent.start_drag()
                            self.drag_start_pos = None
                            break
                        parent = parent.parent()
        else:
            super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event):
        """双击进入编辑状态，已完成任务不允许编辑。"""
        if event.button() == Qt.LeftButton:
            # 父任务已完成时禁止编辑
            parent = self.parent()
            while parent:
                if isinstance(parent, TaskWidget):
                    if parent.is_completed:
                        return
                    break
                parent = parent.parent()

            self.setReadOnly(False)
            self.viewport().setCursor(Qt.IBeamCursor)
            self.setFocus()
            self.clicked.emit(self)
        super().mouseDoubleClickEvent(event)

    def focusOutEvent(self, event):
        """失焦后恢复只读状态。"""
        self.setReadOnly(True)
        self.viewport().setCursor(Qt.ArrowCursor)
        super().focusOutEvent(event)


class TaskWidget(QFrame):
    """
    任务框组件，支持父子层级、拖拽、展开收起
    新增：时间戳、完成状态
    """
    selected = pyqtSignal(object)  
    request_split = pyqtSignal(object) 
    subtask_added = pyqtSignal(object)
    structure_changed = pyqtSignal()
    
    _drag_source = None

    def __init__(self, text="", parent=None):
        """初始化任务控件并建立基础状态。"""
        super().__init__(parent)
        self.setAcceptDrops(True)
        
        self.subtasks = [] 
        self.parent_task = None 
        self.is_expanded = True
        self.is_selected = False
        self.task_id = None
        
        # 新增属性
        self.created_time = datetime.datetime.now()
        self.updated_time = self.created_time
        self.completed_time = None
        self.is_completed = False
        self.is_archived = False
        self.scheduled_date = datetime.date.today()
        
        self.init_ui(text)

    def init_ui(self, text):
        """初始化任务控件的布局与子组件。"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 1. 任务内容行
        self.content_frame = QFrame()
        self.content_layout = QHBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(5)
        
        # 左侧：添加子任务按钮
        self.add_sub_btn = QPushButton("＋")
        self.add_sub_btn.setFixedWidth(25)
        self.add_sub_btn.setFixedHeight(25)
        self.add_sub_btn.setCursor(Qt.PointingHandCursor)
        self.add_sub_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid rgba(255,255,255,100);
                border-radius: 3px;
                color: white;
                background: transparent;
                font-weight: bold;
                text-align: center;
            }
            QPushButton:hover { background: rgba(255,255,255,50); }
        """)
        self.add_sub_btn.clicked.connect(self.add_new_subtask_manual)
        
        # 中间：文本编辑器与时间标签
        self.center_widget = QWidget()
        self.center_layout = QVBoxLayout(self.center_widget)
        self.center_layout.setContentsMargins(0, 0, 0, 0)
        self.center_layout.setSpacing(0)

        self.text_edit = AutoResizingTextEdit()
        self.text_edit.setPlainText(text)
        self.text_edit.clicked.connect(self.handle_selection)
        self.text_edit.textChanged.connect(self.on_text_changed)
        
        # 时间标签展示
        self.time_label = QLabel()
        self.time_label.setStyleSheet("color: rgba(255, 255, 255, 150); font-size: 10px;")
        self.update_time_label()

        self.center_layout.addWidget(self.text_edit)
        self.center_layout.addWidget(self.time_label)

        # 右侧：展开/收起按钮
        self.expand_btn = QPushButton("▼") 
        self.expand_btn.setFixedWidth(25)
        self.expand_btn.setFixedHeight(25)
        self.expand_btn.setCursor(Qt.PointingHandCursor)
        self.expand_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid rgba(255,255,255,0);
                border-radius: 3px;
                color: white;
                background: transparent;
                font-weight: bold;
                text-align: center;
            }
            QPushButton:hover { 
                background: rgba(255,255,255,30); 
                border: 1px solid rgba(255,255,255,50);
            }
        """)
        self.expand_btn.clicked.connect(self.toggle_expand)
        self.expand_btn.hide() 
        
        self.content_layout.addWidget(self.add_sub_btn)
        self.content_layout.addWidget(self.center_widget)
        self.content_layout.addWidget(self.expand_btn)
        
        self.main_layout.addWidget(self.content_frame)
        
        # 子任务容器
        self.subtasks_container = QWidget()
        self.subtasks_layout = QVBoxLayout(self.subtasks_container)
        self.subtasks_layout.setContentsMargins(20, 5, 0, 5)
        self.subtasks_layout.setSpacing(5)
        self.main_layout.addWidget(self.subtasks_container)
        
        self.adjust_size()

    def adjust_size(self):
        """预留尺寸适配接口，当前由子组件自适应。"""
        pass

    def handle_selection(self, _):
        """触发选中信号。"""
        self.selected.emit(self)

    def on_text_changed(self):
        """文本变化时更新时间戳并刷新显示。"""
        self.updated_time = datetime.datetime.now()
        self.update_time_label()
        self.adjust_size()

    def update_time_label(self):
        """刷新时间标签文本。"""
        time_str = self.updated_time.strftime("%m-%d %H:%M")
        status_str = "（已完成）" if self.is_completed else ""
        self.time_label.setText(f"{time_str}{status_str}")

    def set_completed(self):
        """设置为完成状态并更新样式。"""
        if self.is_completed:
            return
            
        self.is_completed = True
        self.completed_time = datetime.datetime.now()
        self.text_edit.setReadOnly(True)
        
        # 样式更新：文本中间划线
        font = self.text_edit.font()
        font.setStrikeOut(True)
        self.text_edit.setFont(font)
        
        self.update_time_label()

        # 通知外部刷新样式
        self.selected.emit(self)

    def set_style(self, text_color, border_color, bg_color, is_light_theme):
        """应用当前主题样式并递归刷新子任务。"""
        current_bg = bg_color
        current_border = border_color
        
        if self.is_completed:
            # 完成状态：灰色背景
            current_bg = "rgba(100, 100, 100, 50)" if is_light_theme else "rgba(50, 50, 50, 100)"
        
        if self.is_selected:
            current_border = f"2px solid {text_color}"
            if is_light_theme and not self.is_completed:
                 current_bg = "rgba(0, 0, 0, 40)"

        self.content_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {current_bg};
                border: {current_border};
                border-radius: 5px;
            }}
        """)
        
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                color: {text_color};
                background: transparent;
                border: none;
                font-family: "Microsoft YaHei";
                font-size: 14px;
            }}
        """)
        
        # 递归设置子任务样式
        for sub in self.subtasks:
            sub.set_style(text_color, border_color, bg_color, is_light_theme)

    def add_new_subtask_manual(self):
        """手动添加子任务并通知管理器绑定。"""
        sub_task = TaskWidget(parent=self)
        sub_task.task_id = generate_task_id()
        sub_task.scheduled_date = getattr(self, "scheduled_date", datetime.date.today())
        self.add_subtask(sub_task)
        self.subtask_added.emit(sub_task)
        self.structure_changed.emit()

    def add_subtask(self, widget):
        """添加子任务控件并更新层级关系。"""
        if not getattr(widget, "task_id", None):
            widget.task_id = generate_task_id()
        if not getattr(widget, "scheduled_date", None):
            widget.scheduled_date = getattr(self, "scheduled_date", datetime.date.today())
        self.subtasks.append(widget)
        self.subtasks_layout.addWidget(widget)
        widget.parent_task = self
        widget.request_split.connect(self.request_split.emit)
        widget.selected.connect(self.selected.emit)
        widget.subtask_added.connect(self.subtask_added.emit)
        widget.structure_changed.connect(self.structure_changed.emit)
        
        self.expand_btn.show()
        if not self.is_expanded:
            self.subtasks_container.hide()
            self.expand_btn.setText("▶")
        else:
            self.subtasks_container.show()
            self.expand_btn.setText("▼")

    def remove_subtask(self, widget):
        """移除子任务控件并更新展开状态。"""
        if widget in self.subtasks:
            self.subtasks.remove(widget)
            widget.deleteLater()
            if not self.subtasks:
                self.expand_btn.hide()
            self.structure_changed.emit()

    def toggle_expand(self):
        """展开或收起子任务区域。"""
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.subtasks_container.show()
            self.expand_btn.setText("▼")
        else:
            self.subtasks_container.hide()
            self.expand_btn.setText("▶")

    def start_drag(self):
        """启动拖拽并设置拖拽源。"""
        TaskWidget._drag_source = self

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.text_edit.toPlainText())
        drag.setMimeData(mime_data)

        pixmap = QPixmap(self.size())
        self.render(pixmap)
        drag.setPixmap(pixmap.scaledToWidth(200))
        drag.setHotSpot(QPoint(100, 15))

        drag.exec_(Qt.MoveAction)

    def mousePressEvent(self, event):
        """记录拖拽起点，避免空白区域无法拖拽。"""
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """拖拽移动触发拖拽启动。"""
        if event.buttons() & Qt.LeftButton and hasattr(self, "drag_start_pos"):
            if (event.pos() - self.drag_start_pos).manhattanLength() > QApplication.startDragDistance():
                self.start_drag()
                if hasattr(self, "drag_start_pos"):
                    del self.drag_start_pos
        super().mouseMoveEvent(event)

    def dragEnterEvent(self, event):
        """允许拖拽进入并避免拖拽到自身或子孙节点。"""
        if event.source() and isinstance(event.source(), TaskWidget):
            source = TaskWidget._drag_source
            if source == self:
                event.ignore()
                return
            if source and self._is_descendant_of_source(source):
                event.ignore()
                return
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """拖拽移动时保持接收状态。"""
        if event.source() and isinstance(event.source(), TaskWidget):
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """处理拖拽放置并更新层级结构。"""
        source = TaskWidget._drag_source
        if source and source != self:
            event.accept()

            pos = event.pos()
            height = self.content_frame.height() or 40

            action = "child"
            if pos.y() < height * 0.25:
                action = "before"
            elif pos.y() > height * 0.75:
                action = "after"

            self._detach_source(source)

            if action == "child":
                self.add_subtask(source)
            else:
                parent_widget = self.parentWidget()
                if parent_widget and parent_widget.layout():
                    layout = parent_widget.layout()
                    index = layout.indexOf(self)
                    target_index = index if action == "before" else index + 1
                    layout.insertWidget(target_index, source)

                    if self.parent_task:
                        try:
                            self_index = self.parent_task.subtasks.index(self)
                            target_list_index = self_index if action == "before" else self_index + 1
                            self.parent_task.subtasks.insert(target_list_index, source)
                        except ValueError:
                            self.parent_task.subtasks.append(source)
                        source.parent_task = self.parent_task
                    else:
                        source.parent_task = None

            source.show()
            source.selected.emit(source)
            self.structure_changed.emit()
        else:
            event.ignore()

    def _detach_source(self, source):
        """从原父级移除拖拽源任务。"""
        if source.parent_task and source in source.parent_task.subtasks:
            source.parent_task.subtasks.remove(source)
            if not source.parent_task.subtasks:
                source.parent_task.expand_btn.hide()
        source.setParent(None)

    def _is_descendant_of_source(self, source):
        """判断当前节点是否为拖拽源的子孙节点。"""
        parent = self.parent_task
        while parent:
            if parent == source:
                return True
            parent = parent.parent_task
        return False

    def to_dict(self):
        """序列化为字典。"""
        return {
            "content": self.text_edit.toPlainText(),
            "created_time": self.created_time.isoformat(),
            "updated_time": self.updated_time.isoformat(),
            "completed_time": self.completed_time.isoformat() if self.completed_time else None,
            "is_completed": self.is_completed,
            "subtasks": [sub.to_dict() for sub in self.subtasks]
        }

def check_and_archive_tasks(task_widgets):
    """
    检查并归档任务
    条件：
    1. 时间进入第二天，时间戳为前一天且未完成的任务
    """
    if not ai_task_manager:
        return

    new_archive = []
    current_time = datetime.datetime.now()
    
    # 定义提取数据的辅助函数
    def extract_task_data(widget):
        return {
            "content": widget.text_edit.toPlainText(),
            "last_updated": widget.updated_time.isoformat(),
            "status": "completed" if widget.is_completed else "pending",
            "completed_time": widget.completed_time.isoformat() if widget.completed_time else None,
        }

    for task in task_widgets:
        if task.is_archived:
            continue
            
        should_archive = False
        
        # 仅归档跨天且未完成的任务，已完成任务保留在当天列表中
        if not task.is_completed:
            task_date = task.updated_time.date()
            if task_date < current_time.date():
                should_archive = True
        
        if should_archive:
            data = extract_task_data(task)
            new_archive.append(data)
            task.is_archived = True
            
    if new_archive:
        ai_task_manager.archive_tasks(new_archive)
        print(f"已归档 {len(new_archive)} 条任务。")

