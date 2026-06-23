from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QStackedWidget, QButtonGroup, QApplication, QLabel, QTextEdit)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from ai_tools import ai_text
except Exception:
    ai_text = None

class SideTabWindow(QWidget):
    """
    独立的侧边页签窗口，悬浮在主窗口外部
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnBottomHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 垂直布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 100, 0, 0) # 顶部留一点空隙
        self.layout.setSpacing(15)
        self.layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        
        # 按钮组
        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)

    def add_tab_btn(self, btn, index):
        self.layout.addWidget(btn)
        self.tab_group.addButton(btn, index)

class TabManager(QWidget):
    """
    管理中间操作区域的内容堆叠，并控制外部的侧边页签窗口
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.panels = []
        # 默认样式缓存
        self.text_color = "white"
        self.border_color = "rgba(255, 255, 255, 50)"
        self.is_light = False
        
        # 创建独立的侧边栏窗口
        self.side_window = SideTabWindow()
        self.side_window.tab_group.buttonClicked.connect(self.on_tab_clicked)
        
        self.init_ui()

    def init_ui(self):
        # 主布局只包含内容堆叠区
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 内容堆叠区
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)

    def add_panel(self, panel, title):
        """添加一个新的面板和对应页签"""
        # 标题文字竖向排列
        vertical_title = "\n".join(list(title))

        # 创建页签按钮
        btn = QPushButton(vertical_title)
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        # 设置固定宽度，高度自适应
        btn.setFixedWidth(30)
        # 稍微设置一个最小高度，避免文字太少时按钮太小
        btn.setMinimumHeight(50)
        
        # 添加到侧边窗口
        self.side_window.add_tab_btn(btn, self.stacked_widget.count())
        
        # 添加面板
        self.stacked_widget.addWidget(panel)
        self.panels.append(panel)
        
        # 如果是第一个，默认选中
        if self.stacked_widget.count() == 1:
            btn.setChecked(True)
            self.on_tab_clicked(btn)
            
        # 应用当前样式到新按钮和新面板
        self.apply_style_to_btn(btn)
        if hasattr(panel, 'update_style'):
            panel.update_style(self.text_color, self.border_color, self.is_light)
            
        # 确保侧边窗口显示
        self.side_window.show()

    def on_tab_clicked(self, btn):
        """点击页签切换面板"""
        index = self.side_window.tab_group.id(btn)
        self.stacked_widget.setCurrentIndex(index)

    def update_style(self, text_color, border_color, is_light_theme):
        """接收主界面的样式更新，并分发给子面板"""
        self.text_color = text_color
        self.border_color = border_color
        self.is_light = is_light_theme
        
        # 更新页签按钮样式
        for btn in self.side_window.tab_group.buttons():
            self.apply_style_to_btn(btn)
            
        # 更新所有子面板样式
        for panel in self.panels:
            if hasattr(panel, 'update_style'):
                panel.update_style(text_color, border_color, is_light_theme)

    def apply_style_to_btn(self, btn, border_side='right'):
        """设置单个页签按钮的样式"""
        btn_hover_bg = "rgba(0, 0, 0, 10)" if self.is_light else "rgba(255, 255, 255, 10)"
        
        # 选中状态下，字体加粗，且左侧有高亮条
        btn.setStyleSheet(f"""
            QPushButton {{
                color: {self.text_color};
                background-color: transparent;
                border: none;
                font-family: "Microsoft YaHei";
                font-size: 15px;
                padding: 5px 2px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover_bg};
                border-radius: 4px;
            }}
            QPushButton:checked {{
                font-weight: bold;
                border-{border_side}: 3px solid {self.text_color};
                background-color: {btn_hover_bg};
            }}
        """)

    def update_sidebar_position(self, main_geo, snapped_side):
        """
        根据主窗口位置更新侧边栏位置
        main_geo: 主窗口的 geometry (QRect)
        snapped_side: 'left' or 'right'
        """
        sidebar_width = 40 # 侧边栏宽度
        
        if snapped_side == 'right':
            # 主窗口在右侧，侧边栏在左侧外部
            x = main_geo.x() - sidebar_width
            self.apply_style_to_btn(self.side_window.tab_group.buttons()[0], 'right')
        else:
            # 主窗口在左侧，侧边栏在右侧外部
            x = main_geo.x() + main_geo.width()
            self.apply_style_to_btn(self.side_window.tab_group.buttons()[0], 'left')
            
        y = main_geo.y()
        h = main_geo.height()
        
        self.side_window.setGeometry(x, y, sidebar_width, h)


class NotePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.text_color = "white"
        self.border_color = "rgba(255, 255, 255, 50)"
        self.is_light = False
        self.init_ui()
        if ai_text:
            ai_text.load_note_to_editor(self.text_edit)
        self.text_edit.textChanged.connect(self.on_text_changed)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        self.title_label = QLabel("记事")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        self.bold_btn = QPushButton("加粗")
        self.italic_btn = QPushButton("斜体")

        for btn in [self.bold_btn, self.italic_btn]:
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(60, 28)
            header_layout.addWidget(btn)

        layout.addLayout(header_layout)

        self.text_edit = QTextEdit()
        self.text_edit.setAcceptRichText(True)
        layout.addWidget(self.text_edit)

        self.bold_btn.clicked.connect(self.on_bold_click)
        self.italic_btn.clicked.connect(self.on_italic_click)

    def on_text_changed(self):
        if ai_text:
            ai_text.save_editor_content(self.text_edit)

    def on_bold_click(self):
        if not ai_text:
            return
        ai_text.toggle_bold(self.text_edit)
        self.sync_style_preferences()

    def on_italic_click(self):
        if not ai_text:
            return
        ai_text.toggle_italic(self.text_edit)
        self.sync_style_preferences()

    def sync_style_preferences(self):
        if not ai_text:
            return
        current_font = self.text_edit.currentFont()
        font_size = int(current_font.pointSize() or 14)
        fmt = self.text_edit.textCursor().charFormat()
        bold = fmt.fontWeight() == QFont.Bold
        italic = fmt.fontItalic()
        ai_text.set_note_style_preferences(
            font_size=font_size,
            bold=bold,
            italic=italic
        )

    def update_style(self, text_color, border_color, is_light_theme):
        self.text_color = text_color
        self.border_color = border_color
        self.is_light = is_light_theme

        btn_hover_bg = "rgba(0, 0, 0, 10)" if is_light_theme else "rgba(255, 255, 255, 10)"
        self.title_label.setStyleSheet(f"color: {text_color}; font-family: 'Microsoft YaHei'; font-size: 14px; font-weight: bold;")
        btn_style = f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {border_color};
                border-radius: 4px;
                color: {text_color};
                font-family: "Microsoft YaHei";
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover_bg};
            }}
        """
        self.bold_btn.setStyleSheet(btn_style)
        self.italic_btn.setStyleSheet(btn_style)

        bg_color = "rgba(120, 120, 120, 80)"
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                color: {text_color};
                font-family: "Microsoft YaHei";
                font-size: 14px;
            }}
        """)
