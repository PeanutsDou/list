from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTextEdit, QFrame, QSizePolicy, QApplication)
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData, QPoint
from PyQt5.QtGui import QDrag, QPixmap, QPainter, QColor

# 同步管理器用于避免 AI 操作与 UI 冲突

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

class AutoResizingTextEdit(QTextEdit):
    """
    自动调整高度的文本输入框
    支持点击选中，双击编辑
    （来自 ui_labels.py）
    """
    # 定义点击信号，传递自身对象
    clicked = pyqtSignal(object)

    def __init__(self, parent=None):
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
        """根据内容调整高度"""
        document = self.document()
        document.setTextWidth(self.viewport().width())
        height = document.size().height()
        
        margins = self.contentsMargins()
        total_height = height + margins.top() + margins.bottom() + 10
        
        self.setFixedHeight(int(max(40, total_height)))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_height()

    def mousePressEvent(self, event):
        # 如果是只读模式（非编辑状态），记录点击位置用于判断拖拽，且不传递给父类以保持箭头光标
        if self.isReadOnly():
            if event.button() == Qt.LeftButton:
                self.drag_start_pos = event.pos()
                self.clicked.emit(self)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.isReadOnly():
            if event.buttons() & Qt.LeftButton and self.drag_start_pos:
                if (event.pos() - self.drag_start_pos).manhattanLength() > QApplication.startDragDistance():
                    # 尝试调用父级(TaskWidget)开始拖拽
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
        if event.button() == Qt.LeftButton:
            self.setReadOnly(False)
            self.viewport().setCursor(Qt.IBeamCursor)
            self.setFocus()
            # 双击时也确保选中
            self.clicked.emit(self)
        super().mouseDoubleClickEvent(event)

    def focusOutEvent(self, event):
        # 失去焦点时变回只读
        self.setReadOnly(True)
        self.viewport().setCursor(Qt.ArrowCursor)
        # 失去焦点不取消选中，由 Manager 管理选中状态的互斥
        super().focusOutEvent(event)


class TaskWidget(QFrame):
    """
    任务框组件，支持父子层级、拖拽、展开收起
    """
    # 信号
    selected = pyqtSignal(object)  # 选中信号
    request_split = pyqtSignal(object) # 请求AI拆分
    
    # 静态变量用于拖拽数据传递（简化版，不用MimeData传复杂对象）
    _drag_source = None

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        
        # 数据结构
        self.subtasks = []  # 存储子 TaskWidget
        self.parent_task = None # 父任务控件
        self.is_expanded = True
        self.is_selected = False
        
        self.init_ui(text)

    def init_ui(self, text):
        # 主垂直布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 1. 任务内容行（水平布局）
        self.content_frame = QFrame()
        self.content_layout = QHBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(5)
        
        # 左侧：添加子任务按钮 (+)
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
        
        # 中间：文本编辑器
        self.text_edit = AutoResizingTextEdit()
        self.text_edit.setPlainText(text)
        self.text_edit.clicked.connect(self.handle_selection)
        # 转发高度变化，调整自身
        self.text_edit.textChanged.connect(self.adjust_size)
        
        # 右侧：展开/收起按钮 (>)
        self.expand_btn = QPushButton("▼") # 默认展开，用向下箭头
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
        self.expand_btn.hide() # 初始无子任务，隐藏
        
        self.content_layout.addWidget(self.add_sub_btn)
        self.content_layout.addWidget(self.text_edit)
        self.content_layout.addWidget(self.expand_btn)
        
        self.main_layout.addWidget(self.content_frame)
        
        # 2. 子任务容器（垂直布局）
        self.subtasks_container = QWidget()
        self.subtasks_layout = QVBoxLayout(self.subtasks_container)
        self.subtasks_layout.setContentsMargins(20, 5, 0, 5) # 左缩进
        self.subtasks_layout.setSpacing(5)
        self.main_layout.addWidget(self.subtasks_container)
        
        # 初始高度适配
        self.adjust_size()

    def adjust_size(self):
        # QFrame 的高度会自动适配内容，不需要手动 setFixedSize，
        # 但 AutoResizingTextEdit 需要 textChanged 触发 layout 更新
        pass

    def handle_selection(self, _):
        self.selected.emit(self)

    def set_style(self, text_color, border_color, bg_color, is_light_theme):
        # 传递给 text_edit
        # 这里需要模拟 TaskListManager 中的 apply_task_style 逻辑
        # 或者直接暴露属性让外部设置
        
        border_style = f"2px solid {text_color}" if self.is_selected else f"1px solid {border_color}"
        actual_bg = "rgba(0, 0, 0, 40)" if (self.is_selected and is_light_theme) else bg_color
        if self.is_selected and not is_light_theme:
            actual_bg = "rgba(255, 255, 255, 40)"
            
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {actual_bg};
                color: {text_color};
                border: {border_style};
                border-radius: 5px;
                padding: 5px;
                font-family: "Microsoft YaHei";
                font-size: 14px;
            }}
        """)
        
        # 按钮颜色
        btn_color = text_color
        self.add_sub_btn.setStyleSheet(f"""
            QPushButton {{
                border: 1px solid {border_color};
                border-radius: 3px;
                color: {btn_color};
                background: transparent;
                font-weight: bold;
                text-align: center;
            }}
            QPushButton:hover {{ background: {border_color}; color: {bg_color}; }}
        """)
        self.expand_btn.setStyleSheet(f"""
            QPushButton {{
                border: 1px solid rgba(255,255,255,0);
                border-radius: 3px;
                color: {btn_color};
                background: transparent;
                font-weight: bold;
                text-align: center;
            }}
            QPushButton:hover {{ 
                background: {border_color}; 
                color: {bg_color}; 
                border: 1px solid {border_color};
            }}
        """)
        
        # 递归更新子任务
        for sub in self.subtasks:
            sub.set_style(text_color, border_color, bg_color, is_light_theme)

    def add_subtask(self, task_widget, index=-1):
        """添加现有的 TaskWidget 作为子任务"""
        if index < 0 or index >= len(self.subtasks):
            self.subtasks.append(task_widget)
            self.subtasks_layout.addWidget(task_widget)
        else:
            self.subtasks.insert(index, task_widget)
            self.subtasks_layout.insertWidget(index, task_widget)
            
        task_widget.parent_task = self
        
        # 显示展开按钮
        self.expand_btn.show()
        if not self.is_expanded:
            task_widget.hide()
        else:
            task_widget.show()
            
    def add_new_subtask_manual(self):
        """手动添加一个新的空白子任务"""
        if get_sync_manager().is_ai_processing():
            return
        new_task = TaskWidget("", self)
        
        self.add_subtask(new_task)
        
        # 临时方案：直接在这里处理样式，稍后在 Manager 中统一处理
        new_task.selected.connect(self.selected.emit) # 转发选中信号
        
        new_task.text_edit.setReadOnly(False)
        new_task.text_edit.setFocus()
        self.selected.emit(new_task) # 选中新任务

    def remove_subtask(self, task_widget):
        if task_widget in self.subtasks:
            self.subtasks.remove(task_widget)
            self.subtasks_layout.removeWidget(task_widget)
            task_widget.setParent(None)
            task_widget.deleteLater()
            
            if not self.subtasks:
                self.expand_btn.hide()

    def toggle_expand(self):
        self.is_expanded = not self.is_expanded
        self.expand_btn.setText("▼" if self.is_expanded else "▶")
        self.subtasks_container.setVisible(self.is_expanded)

    # --- 拖拽与放置 ---
    def start_drag(self):
        """开始拖拽逻辑，供内部或子组件调用"""
        TaskWidget._drag_source = self
        
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.text_edit.toPlainText()) # 携带文本供参考
        drag.setMimeData(mime_data)
        
        # 简单的拖拽反馈
        pixmap = QPixmap(self.size())
        self.render(pixmap)
        drag.setPixmap(pixmap.scaledToWidth(200))
        drag.setHotSpot(QPoint(100, 15))
        
        # 开始拖拽
        drag.exec_(Qt.MoveAction)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 如果点击的是 text_edit 区域，text_edit 会截获，不会到这里
            # 这里处理点击边缘或空白处
            self.drag_start_pos = event.pos()
        
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and hasattr(self, 'drag_start_pos'):
            if (event.pos() - self.drag_start_pos).manhattanLength() > QApplication.startDragDistance():
                self.start_drag()
                # 拖拽结束后重置
                if hasattr(self, 'drag_start_pos'):
                    del self.drag_start_pos
        super().mouseMoveEvent(event)

    def dragEnterEvent(self, event):
        if event.source() and isinstance(event.source(), TaskWidget):
            # 防止拖到自己或自己的子孙节点中
            source = TaskWidget._drag_source
            if source == self:
                event.ignore()
                return
            
            # 检查 self 是否是 source 的子孙
            parent = self.parent_task
            while parent:
                if parent == source:
                    event.ignore()
                    return
                parent = parent.parent_task
                
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.source() and isinstance(event.source(), TaskWidget):
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        source = TaskWidget._drag_source
        if source and source != self:
            event.accept()
            
            # 判断拖放位置：
            # 上 25% -> 插入到上方 (作为兄弟)
            # 下 25% -> 插入到下方 (作为兄弟)
            # 中间 50% -> 成为子任务
            
            pos = event.pos()
            height = self.content_frame.height() # 只看内容区域高度，不包括展开的子任务区域
            if height == 0: height = 40 # 防御
            
            action = "child"
            if pos.y() < height * 0.25:
                action = "before"
            elif pos.y() > height * 0.75:
                action = "after"
                
            # 执行移动
            # 1. 先从原父节点移除 (但不销毁)
            self._detach_source(source)
            
            if action == "child":
                self.add_subtask(source)
            else:
                # 插入到 self 的兄弟节点位置
                parent_widget = self.parentWidget() # 子任务容器或顶层容器
                if parent_widget and parent_widget.layout():
                    layout = parent_widget.layout()
                    index = layout.indexOf(self)
                    
                    target_index = index if action == "before" else index + 1
                    
                    layout.insertWidget(target_index, source)
                    
                    # 更新逻辑结构
                    if self.parent_task:
                        # 找到我在父任务列表中的索引，保持一致性
                        try:
                            self_index = self.parent_task.subtasks.index(self)
                            target_list_index = self_index if action == "before" else self_index + 1
                            self.parent_task.subtasks.insert(target_list_index, source)
                        except ValueError:
                            self.parent_task.subtasks.append(source)
                        source.parent_task = self.parent_task
                    else:
                        source.parent_task = None
                        # 如果是顶层，不需要维护 subtasks 列表，因为没有 parent_task
            
            source.show()
            # 触发选中
            source.selected.emit(source)
            
        else:
            event.ignore()

    def _detach_source(self, source):
        """将 source 从其父节点移除，准备移动"""
        if source.parent_task:
            if source in source.parent_task.subtasks:
                source.parent_task.subtasks.remove(source)
                # 隐藏父节点的展开按钮如果需要
                if not source.parent_task.subtasks:
                    source.parent_task.expand_btn.hide()
                    
        # 从布局中移除
        source.setParent(None)

    def get_all_subtasks_text(self):
        """递归获取所有子任务文本"""
        pass
