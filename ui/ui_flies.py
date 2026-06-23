import os
import sys
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QHBoxLayout, QMessageBox, QMenu
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from ai_files_tools.ai_files_getfiles import get_common_files, add_common_file, record_open
    from ai_files_tools.ai_files_remove import remove_common_file
    from ai_konwledge.web_konwledge.ai_web import list_favorite_urls, remove_favorite_url
    from ai_web_tools.ai_web_open import open_url
except Exception:
    def get_common_files():
        return {"items": []}
    def add_common_file(path):
        return {"success": False}
    def record_open(path):
        return {"success": False}
    def remove_common_file(path):
        return {"success": False}
    def list_favorite_urls(limit=0):
        return {"items": []}
    def remove_favorite_url(keyword):
        return {"success": False}
    def open_url(url):
        return {"status": "error"}


class FilePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.text_color = "white"
        self.border_color = "rgba(255, 255, 255, 50)"
        self.is_light = False
        self.init_ui()
        self.load_files()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()

        self.title_label = QLabel("常用文件")
        self.title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setFixedSize(60, 28)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.load_files)

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_btn)
        layout.addLayout(header_layout)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)
        self.list_widget.itemDoubleClicked.connect(self.open_selected_item)
        self.list_widget.setAcceptDrops(True)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.list_widget)

        fav_header_layout = QHBoxLayout()
        self.fav_title_label = QLabel("收藏网址")
        self.fav_title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        self.fav_title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.fav_refresh_btn = QPushButton("刷新")
        self.fav_refresh_btn.setFixedSize(60, 28)
        self.fav_refresh_btn.setCursor(Qt.PointingHandCursor)
        self.fav_refresh_btn.clicked.connect(self.load_favorites)

        fav_header_layout.addWidget(self.fav_title_label)
        fav_header_layout.addStretch()
        fav_header_layout.addWidget(self.fav_refresh_btn)
        layout.addLayout(fav_header_layout)

        self.fav_list_widget = QListWidget()
        self.fav_list_widget.setSelectionMode(QListWidget.SingleSelection)
        self.fav_list_widget.itemDoubleClicked.connect(self.open_selected_favorite)
        self.fav_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.fav_list_widget.customContextMenuRequested.connect(self.show_favorite_context_menu)
        layout.addWidget(self.fav_list_widget)

        self.setAcceptDrops(True)

    def load_files(self):
        data = get_common_files()
        items = data.get("items", [])
        self.list_widget.clear()

        if not items:
            placeholder = QListWidgetItem("暂无常用文件，请拖入文件或文件夹")
            placeholder.setFlags(placeholder.flags() & ~Qt.ItemIsSelectable)
            self.list_widget.addItem(placeholder)
            return

        for item in items:
            display_text = self.build_display_text(item)
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.UserRole, item.get("path"))
            list_item.setToolTip(item.get("path", ""))
            self.list_widget.addItem(list_item)

        self.load_favorites()

    def load_favorites(self):
        data = list_favorite_urls()
        items = data.get("items", [])
        self.fav_list_widget.clear()

        if not items:
            placeholder = QListWidgetItem("暂无收藏网址")
            placeholder.setFlags(placeholder.flags() & ~Qt.ItemIsSelectable)
            self.fav_list_widget.addItem(placeholder)
            return

        for item in items:
            title = item.get("title") or item.get("url", "")
            url = item.get("url", "")
            list_item = QListWidgetItem(title)
            list_item.setData(Qt.UserRole, url)
            list_item.setToolTip(url)
            self.fav_list_widget.addItem(list_item)

    def build_display_text(self, item):
        name = item.get("name", "")
        is_dir = item.get("is_dir", False)
        size_text = item.get("size_text", "")
        modified_time = item.get("modified_time", "")
        type_text = "文件夹" if is_dir else "文件"
        size_part = "" if is_dir else size_text
        parts = [name, type_text, size_part, modified_time]
        return "  |  ".join([p for p in parts if p])

    def open_selected_item(self, item):
        path = item.data(Qt.UserRole)
        if not path:
            return
        if not os.path.exists(path):
            QMessageBox.warning(self, "打开失败", "文件或文件夹不存在。")
            return
        try:
            record_open(path)
            os.startfile(path)
        except Exception:
            QMessageBox.warning(self, "打开失败", "无法打开目标路径。")
        self.load_files()

    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        path = item.data(Qt.UserRole)
        if not path:
            return
        menu = QMenu(self)
        remove_action = menu.addAction("移除")
        action = menu.exec_(self.list_widget.mapToGlobal(pos))
        if action == remove_action:
            remove_common_file(path)
            self.load_files()

    def open_selected_favorite(self, item):
        url = item.data(Qt.UserRole)
        if not url:
            return
        result = open_url(url)
        if result.get("status") != "success":
            QMessageBox.warning(self, "打开失败", "无法打开目标网址。")

    def show_favorite_context_menu(self, pos):
        item = self.fav_list_widget.itemAt(pos)
        if not item:
            return
        url = item.data(Qt.UserRole)
        if not url:
            return
        menu = QMenu(self)
        remove_action = menu.addAction("移除")
        action = menu.exec_(self.fav_list_widget.mapToGlobal(pos))
        if action == remove_action:
            remove_favorite_url(url)
            self.load_favorites()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        for url in event.mimeData().urls():
            if url.isLocalFile():
                add_common_file(url.toLocalFile())
        event.acceptProposedAction()
        self.load_files()

    def update_style(self, text_color, border_color, is_light_theme):
        self.text_color = text_color
        self.border_color = border_color
        self.is_light = is_light_theme

        bg_color = "rgba(120, 120, 120, 80)"
        item_hover = "rgba(255, 255, 255, 40)" if not is_light_theme else "rgba(0, 0, 0, 20)"
        item_selected = "rgba(255, 255, 255, 80)" if not is_light_theme else "rgba(0, 0, 0, 40)"

        self.title_label.setStyleSheet(f"color: {text_color};")
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {border_color};
                border-radius: 4px;
                color: {text_color};
                font-family: "Microsoft YaHei";
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 30);
            }}
        """)

        self.fav_title_label.setStyleSheet(f"color: {text_color};")
        self.fav_refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {border_color};
                border-radius: 4px;
                color: {text_color};
                font-family: "Microsoft YaHei";
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 30);
            }}
        """)

        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                color: {text_color};
                font-family: "Microsoft YaHei";
                selection-background-color: {item_selected};
                selection-color: {text_color};
            }}
            QListWidget::item {{
                padding: 6px 8px;
            }}
            QListWidget::item:hover {{
                background-color: {item_hover};
            }}
        """)

        self.fav_list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                color: {text_color};
                font-family: "Microsoft YaHei";
                selection-background-color: {item_selected};
                selection-color: {text_color};
            }}
            QListWidget::item {{
                padding: 6px 8px;
            }}
            QListWidget::item:hover {{
                background-color: {item_hover};
            }}
        """)
