from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFrame, QGridLayout, QPushButton, QHBoxLayout, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
import sys
import os
import json
from datetime import datetime, timedelta

# 确保能导入 ai_tools
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)
UI_STATE_FILE = os.path.join(current_dir, "ui_state.json")

# 导入 AI 业务模块
try:
    from ai_tools import ai_statistics
    from ai_tools import ai_task_manager
    from tools import token_cal
except ImportError:
    print("警告：无法导入 ai_tools 模块")
    # 兜底实现
    class MockStats:
        def calculate_history_stats(self):
            return {"total_completed": 0, "total_uncompleted": 0, "yesterday_completed": 0, "yesterday_uncompleted": 0}
    ai_statistics = MockStats()
    class MockTM:
        def clear_all_history(self): pass
    ai_task_manager = MockTM()
    class MockTokenCal:
        def get_total_summary(self):
            return {"tokens": 0, "cost": 0.0}
        def query_usage(self, date=None, start_date=None, end_date=None, period="day"):
            return {"success": True, "tokens": 0, "cost": 0.0}
    token_cal = MockTokenCal()

class HistoryPanel(QWidget):
    """
    历史数据展示面板
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.text_color = "white"
        self.border_color = "rgba(255, 255, 255, 50)"
        self.is_light = False
        
        self.init_ui()
        
        # 定时刷新数据 (每次显示时刷新也可以，这里简单用定时器每5秒刷新一次)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(5000)
        
        self.refresh_data()
        self._apply_saved_ui_state()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 顶部栏 (标题 + 清空按钮)
        top_bar = QHBoxLayout()
        
        # 标题
        title = QLabel("历史统计")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        self.title_label = title
        
        # 清空按钮
        self.clear_btn = QPushButton("清空历史数据")
        self.clear_btn.setFixedSize(120, 30)
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_history_data)
        
        # 使用 stretch 让标题居中，按钮在右边
        # 左边加一个占位，让标题大致居中
        dummy = QWidget()
        dummy.setFixedSize(120, 30)
        
        top_bar.addWidget(dummy)
        top_bar.addStretch()
        top_bar.addWidget(title)
        top_bar.addStretch()
        top_bar.addWidget(self.clear_btn)
        
        layout.addLayout(top_bar)
        
        # 统计网格
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(15)
        
        self.stat_labels = {}
        
        # 创建4个统计块
        self.create_stat_block("历史已完成", 0, 0, "total_completed")
        self.create_stat_block("历史未完成", 0, 1, "total_uncompleted")
        self.create_stat_block("昨日已完成", 1, 0, "yesterday_completed")
        self.create_stat_block("昨日未完成", 1, 1, "yesterday_uncompleted")
        self.create_stat_block("今日Token消耗", 2, 0, "token_day")
        self.create_stat_block("本月Token消耗", 2, 1, "token_month")
        self.create_stat_block("本年Token消耗", 3, 0, "token_year")
        self.create_stat_block("累计Token消耗", 3, 1, "token_total")
        
        layout.addLayout(self.grid_layout)
        
        layout.addStretch()

    def create_stat_block(self, title_text, row, col, key):
        frame = QFrame()
        frame.setObjectName("StatFrame")
        
        v_layout = QVBoxLayout(frame)
        v_layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel(title_text)
        title.setFont(QFont("Microsoft YaHei", 10))
        title.setAlignment(Qt.AlignCenter)
        
        value = QLabel("0")
        value.setFont(QFont("Arial", 24, QFont.Bold))
        value.setAlignment(Qt.AlignCenter)
        
        v_layout.addWidget(value)
        v_layout.addWidget(title)
        
        self.grid_layout.addWidget(frame, row, col)
        
        self.stat_labels[key] = {
            "frame": frame,
            "title": title,
            "value": value
        }

    def clear_history_data(self):
        """清空历史数据"""
        # 确认对话框
        reply = QMessageBox.question(self, '确认', 
                                     "确定要清空所有历史数据吗？此操作不可恢复。",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            ai_task_manager.clear_all_history()
            self.refresh_data()

    def refresh_data(self):
        """读取 JSON 并更新统计"""
        # 使用 ai_statistics 模块获取统计数据
        stats = ai_statistics.calculate_history_stats()
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")
        year = datetime.now().strftime("%Y")
        day_usage = token_cal.query_usage(date=today, period="day")
        month_usage = token_cal.query_usage(date=month, period="month")
        year_usage = token_cal.query_usage(date=year, period="year")
        total_usage = token_cal.get_total_summary()
        stats["token_day"] = day_usage if isinstance(day_usage, dict) else {"tokens": 0, "cost": 0.0}
        stats["token_month"] = month_usage if isinstance(month_usage, dict) else {"tokens": 0, "cost": 0.0}
        stats["token_year"] = year_usage if isinstance(year_usage, dict) else {"tokens": 0, "cost": 0.0}
        stats["token_total"] = total_usage if isinstance(total_usage, dict) else {"tokens": 0, "cost": 0.0}
        
        # 更新 UI
        for key, value in stats.items():
            if key in self.stat_labels:
                if key.startswith("token_") and isinstance(value, dict):
                    tokens = value.get("tokens", 0)
                    cost = value.get("cost", 0.0)
                    self.stat_labels[key]["value"].setText(f"{tokens}\n{cost:.6f}元")
                else:
                    self.stat_labels[key]["value"].setText(str(value))

    def _load_ui_state(self):
        if not os.path.exists(UI_STATE_FILE):
            return {}
        try:
            with open(UI_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_ui_state(self, data):
        try:
            os.makedirs(os.path.dirname(UI_STATE_FILE), exist_ok=True)
            with open(UI_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            pass

    def _apply_saved_ui_state(self):
        data = self._load_ui_state()
        state = data.get("history_panel", {})
        width = state.get("width")
        height = state.get("height")
        if isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0:
            self.resize(width, height)

    def resizeEvent(self, event):
        data = self._load_ui_state()
        data["history_panel"] = {"width": self.width(), "height": self.height()}
        self._save_ui_state(data)
        super().resizeEvent(event)

    def update_style(self, text_color, border_color, is_light_theme):
        self.text_color = text_color
        self.border_color = border_color
        self.is_light = is_light_theme
        
        self.title_label.setStyleSheet(f"color: {text_color};")
        
        bg_color = "rgba(0, 0, 0, 30)" if is_light_theme else "rgba(255, 255, 255, 10)"
        
        # 按钮样式
        btn_hover = "rgba(0, 0, 0, 20)" if is_light_theme else "rgba(255, 255, 255, 30)"
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {border_color};
                border-radius: 5px;
                color: {text_color};
                font-family: "Microsoft YaHei";
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
        """)
        
        for key, widgets in self.stat_labels.items():
            frame = widgets["frame"]
            frame.setStyleSheet(f"""
                #StatFrame {{
                    background-color: {bg_color};
                    border: 1px solid {border_color};
                    border-radius: 8px;
                }}
            """)
            
            widgets["title"].setStyleSheet(f"color: {text_color}; opacity: 0.8;")
            widgets["value"].setStyleSheet(f"color: {text_color};")
