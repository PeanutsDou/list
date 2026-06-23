import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, 
                             QLabel, QSlider, QComboBox, QPushButton, 
                             QGroupBox, QFrame, QHBoxLayout, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QColor, QFont, QCursor
from .ui_labels import TaskListManager
from .ui_tap import TabManager, NotePanel
from .ui_history import HistoryPanel
from .ui_chat import ChatPanel
from .ui_flies import FilePanel
from .ui_rili import CalendarStripWidget
from .ui_settings import SettingsPanel

class DesktopSideBar(QWidget):
    """
    桌面侧边栏窗口类
    
    功能特点：
    1. 实时检测屏幕高度，支持左右自动吸附。
    2. 高度适配屏幕可用区域（不遮挡任务栏）。
    3. 始终位于底部，不可最小化，无边框。
    4. 提供颜色调节功能。
    5. 支持鼠标拖动位置，释放后自动吸附。
    6. 支持拖动边缘调整宽度。
    """
    
    def __init__(self):
        super().__init__()
        
        # 默认参数
        self.default_width = 500
        self.min_width = 100
        self.max_width = 800
        self.current_color = QColor(0, 0, 0) # 默认纯黑
        self.current_alpha = 204 # 固定透明度 (0.8 * 255)   
        
        # 状态变量
        self.is_dragging = False
        self.is_resizing = False
        self.drag_start_pos = QPoint()
        self.resize_edge_margin = 50  # 增加边缘判定距离，提高灵敏度
        self.snapped_side = 'right'   # 'left' or 'right'
        
        # 初始化窗口设置
        self.init_window_flags()
        
        # 初始化 UI
        self.init_ui()
        
        # 监听屏幕变化信号
        self.screen = QApplication.primaryScreen()
        self.screen.availableGeometryChanged.connect(self.update_geometry_to_screen)
        self.screen.geometryChanged.connect(self.update_geometry_to_screen)
        
        # 初始吸附
        self.update_geometry_to_screen()

    def init_window_flags(self):
        """设置窗口标志，实现无边框、置底、工具窗口属性"""
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnBottomHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

    def init_ui(self):
        """初始化用户界面控件"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 40, 20, 20)
        main_layout.setSpacing(15)
        self.setLayout(main_layout)
        
        # 标题
        title_label = QLabel("桌面AI助手")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: rgba(128, 128, 128, 100);")
        main_layout.addWidget(line)
        
        # --- 任务清单区域 ---
        # 使用 TabManager 管理面板
        self.tab_manager = TabManager()
        main_layout.addWidget(self.tab_manager)
        
        # 初始化任务清单面板并添加到 TabManager
        self.task_manager = TaskListManager()
        self.tab_manager.add_panel(self.task_manager, "任务")
        
        # 初始化聊天面板
        self.chat_panel = ChatPanel()
        self.tab_manager.add_panel(self.chat_panel, "聊聊")
        self.chat_panel.tasks_updated.connect(self.task_manager.load_tasks_from_file)
        
        # 初始化文件面板
        self.file_panel = FilePanel()
        self.tab_manager.add_panel(self.file_panel, "文件")
        # 任务或文件更新后同步刷新文件面板列表
        self.chat_panel.tasks_updated.connect(self.file_panel.load_files)

        self.note_panel = NotePanel()
        self.tab_manager.add_panel(self.note_panel, "记事")

        # 初始化记录面板
        self.history_panel = HistoryPanel()
        self.tab_manager.add_panel(self.history_panel, "记录")
        self.chat_panel.tasks_updated.connect(self.history_panel.refresh_data)

        self.calendar_widget = CalendarStripWidget()
        self.calendar_widget.date_changed.connect(self.task_manager.set_current_date)
        main_layout.addWidget(self.calendar_widget)
        
        # --- 底部设置区域 ---
        
        # 设置切换按钮
        self.toggle_settings_btn = QPushButton("显示设置 (展开/收起)")
        self.toggle_settings_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(128, 128, 128, 50);
                color: white;
                border: none;
                padding: 5px;
                border-radius: 4px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: rgba(128, 128, 128, 80);
            }
        """)
        self.toggle_settings_btn.setCheckable(True)
        self.toggle_settings_btn.clicked.connect(self.toggle_settings)
        main_layout.addWidget(self.toggle_settings_btn)

        # 设置面板（默认隐藏）
        self.control_group = QGroupBox()
        self.control_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid rgba(128, 128, 128, 100);
                border-radius: 5px;
                padding-top: 10px;
                background-color: rgba(0, 0, 0, 50);
            }
        """)
        control_layout = QVBoxLayout()
        self.control_group.setLayout(control_layout)
        self.control_group.setVisible(False) # 默认收起
        
        # 颜色选择
        color_label = QLabel("背景颜色:")
        control_layout.addWidget(color_label)
        
        self.color_combo = QComboBox()
        self.colors = {
            "纯黑": QColor(0, 0, 0),
            "深灰": QColor(30, 30, 30),
        }
        self.color_combo.addItems(self.colors.keys())
        self.color_combo.setCurrentText("纯黑")
        self.color_combo.currentIndexChanged.connect(self.change_color)
        control_layout.addWidget(self.color_combo)
        
        # 添加开机自启设置
        self.settings_panel = SettingsPanel()
        control_layout.addWidget(self.settings_panel)
        
        main_layout.addWidget(self.control_group)
        
        # 退出按钮
        quit_btn = QPushButton("关闭")
        quit_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 40);
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(255, 50, 50, 40);
            }
        """)
        quit_btn.clicked.connect(QApplication.instance().quit)
        main_layout.addWidget(quit_btn)
        
        self.update_style()

    def toggle_settings(self):
        """切换设置面板的显示/隐藏"""
        is_visible = self.toggle_settings_btn.isChecked()
        self.control_group.setVisible(is_visible)
        if is_visible:
            self.toggle_settings_btn.setText("显示设置 (收起)")
        else:
            self.toggle_settings_btn.setText("显示设置 (展开)")

    def update_geometry_to_screen(self):
        """根据吸附状态调整窗口位置"""
        screen_geo = QApplication.primaryScreen().availableGeometry()
        
        if self.snapped_side == 'right':
            x = screen_geo.x() + screen_geo.width() - self.default_width
        else: # left
            x = screen_geo.x()
            
        y = screen_geo.y()
        h = screen_geo.height()
        
        self.setGeometry(x, y, self.default_width, h)
        self.lower()
        
        # 更新侧边页签位置
        if hasattr(self, 'tab_manager'):
            self.tab_manager.update_sidebar_position(self.geometry(), self.snapped_side)

    def change_color(self, index):
        color_name = self.color_combo.currentText()
        if color_name in self.colors:
            self.current_color = self.colors[color_name]
            self.update_style()

    def update_style(self):
        """更新样式，确保文字颜色对比度"""
        r, g, b = self.current_color.red(), self.current_color.green(), self.current_color.blue()
        a = self.current_alpha
        
        # 计算亮度，决定文字颜色 (YIQ公式)
        # 亮度 > 128 (或者更保险的 186) 则用黑色
        is_light = (r*0.299 + g*0.587 + b*0.114) > 180
        text_color = "black" if is_light else "white"
        border_color = "rgba(0,0,0,50)" if is_light else "rgba(255,255,255,50)"
        
        # 使用 rgba 设置背景色，这样只会影响背景透明度，不会影响子控件的文字不透明度
        self.setStyleSheet(f"""
            DesktopSideBar {{
                background-color: rgba({r}, {g}, {b}, {a});
            }}
            QLabel {{
                color: {text_color};
                background-color: transparent;
            }}
            QGroupBox {{
                border: 1px solid {border_color};
                color: {text_color};
                background-color: rgba(0, 0, 0, 50); /* 设置面板保持半透明背景 */
            }}
            QComboBox {{
                border: 1px solid {border_color};
                padding: 5px;
                color: {text_color};
                background-color: rgba(255, 255, 255, 20);
            }}
            QComboBox QAbstractItemView {{
                background-color: rgb(50, 50, 50);
                color: white;
                selection-background-color: rgb(80, 80, 80);
            }}
            QPushButton {{
                color: {text_color};
            }}
        """)
        
        # 更新 TabManager 的样式 (它会自动更新子面板如 TaskManager)
        if hasattr(self, 'tab_manager'):
            self.tab_manager.update_style(text_color, border_color, is_light)
            
        # 更新设置面板样式
        if hasattr(self, 'settings_panel'):
            self.settings_panel.update_style(text_color)

    # --- 鼠标事件处理 ---

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.check_resize_area(event.pos()):
                self.is_resizing = True
            else:
                self.is_dragging = True
            self.drag_start_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if not self.is_dragging and not self.is_resizing:
            if self.check_resize_area(event.pos()):
                self.setCursor(Qt.SizeHorCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

        if self.is_resizing:
            self.handle_resize(event.globalPos())
            event.accept()
            return

        if self.is_dragging:
            self.move(event.globalPos() - self.drag_start_pos)
            # 拖动时实时更新侧边栏位置
            if hasattr(self, 'tab_manager'):
                self.tab_manager.update_sidebar_position(self.geometry(), self.snapped_side)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.is_dragging:
                self.snap_to_edge()
                self.is_dragging = False
            if self.is_resizing:
                self.is_resizing = False
            self.setCursor(Qt.ArrowCursor)

    def check_resize_area(self, pos):
        if self.snapped_side == 'right':
            return pos.x() <= self.resize_edge_margin 
        else:
            return pos.x() >= self.width() - self.resize_edge_margin

    def handle_resize(self, global_mouse_pos):
        screen_geo = QApplication.primaryScreen().availableGeometry()
        
        if self.snapped_side == 'right':
            new_left = global_mouse_pos.x()
            right_edge = screen_geo.x() + screen_geo.width()
            new_width = right_edge - new_left
            
            if self.min_width <= new_width <= self.max_width:
                self.setGeometry(new_left, screen_geo.y(), new_width, screen_geo.height())
                self.default_width = new_width
                
        else:
            left_edge = screen_geo.x()
            new_width = global_mouse_pos.x() - left_edge
            
            if self.min_width <= new_width <= self.max_width:
                self.setGeometry(left_edge, screen_geo.y(), new_width, screen_geo.height())
                self.default_width = new_width
        
        # 更新侧边页签位置
        if hasattr(self, 'tab_manager'):
            self.tab_manager.update_sidebar_position(self.geometry(), self.snapped_side)

    def snap_to_edge(self):
        screen_geo = QApplication.primaryScreen().availableGeometry()
        center_x = self.x() + self.width() / 2
        screen_center_x = screen_geo.x() + screen_geo.width() / 2
        
        if center_x < screen_center_x:
            self.snapped_side = 'left'
        else:
            self.snapped_side = 'right'
            
        self.update_geometry_to_screen()

    def showEvent(self, event):
        super().showEvent(event)
        self.update_geometry_to_screen()
        self.lower()

    def closeEvent(self, event):
        # 确保关闭时同时关闭侧边栏
        if hasattr(self, 'tab_manager'):
            self.tab_manager.side_window.close()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DesktopSideBar()
    window.show()
    sys.exit(app.exec_())
