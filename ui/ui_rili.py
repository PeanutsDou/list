import datetime
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFrame, QCalendarWidget
from PyQt5.QtCore import Qt, pyqtSignal, QDate, QTimer


class CalendarStripWidget(QWidget):
    date_changed = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.system_date = datetime.date.today()
        self.init_ui()
        self.init_timer()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(6)

        self.toggle_btn = QPushButton("日历 (展开/收起)")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(128, 128, 128, 50);
                color: white;
                border: none;
                padding: 6px;
                border-radius: 4px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: rgba(128, 128, 128, 80);
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_calendar)
        self.main_layout.addWidget(self.toggle_btn)

        self.calendar_container = QFrame()
        self.calendar_container.setStyleSheet("""
            QFrame {
                border: 1px solid rgba(255, 255, 255, 90);
                border-radius: 6px;
                background-color: rgba(0, 0, 0, 120);
            }
        """)
        container_layout = QVBoxLayout(self.calendar_container)
        container_layout.setContentsMargins(6, 6, 6, 6)
        container_layout.setSpacing(0)

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar.setSelectedDate(QDate.currentDate())
        self.calendar.selectionChanged.connect(self.on_calendar_changed)
        self.calendar.setStyleSheet("""
            QCalendarWidget {
                background-color: rgba(0, 0, 0, 120);
                color: white;
                border: none;
                selection-background-color: white;
                selection-color: black;
            }
            QCalendarWidget QWidget {
                background-color: rgba(0, 0, 0, 120);
                color: white;
            }
            QCalendarWidget QToolButton {
                background-color: rgba(0, 0, 0, 120);
                color: white;
                border: none;
                margin: 2px;
                padding: 4px 6px;
                border-radius: 4px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: rgba(0, 0, 0, 160);
            }
            QCalendarWidget QMenu {
                background-color: rgba(0, 0, 0, 220);
                color: white;
            }
            QCalendarWidget QSpinBox {
                background-color: rgba(0, 0, 0, 140);
                color: white;
                border: none;
                padding: 2px 4px;
                border-radius: 3px;
            }
            QCalendarWidget QAbstractItemView:enabled {
                background-color: rgba(0, 0, 0, 120);
                color: white;
                selection-background-color: white;
                selection-color: black;
            }
            QCalendarWidget QAbstractItemView:disabled {
                color: rgba(255, 255, 255, 100);
            }
        """)

        container_layout.addWidget(self.calendar)
        self.calendar_container.setVisible(False)
        self.main_layout.addWidget(self.calendar_container)

        self.emit_current_date()

    def init_timer(self):
        self.auto_timer = QTimer(self)
        self.auto_timer.timeout.connect(self.check_system_date)
        self.auto_timer.start(60000)

    def toggle_calendar(self):
        is_visible = self.toggle_btn.isChecked()
        self.calendar_container.setVisible(is_visible)
        self.toggle_btn.setText("日历 (收起)" if is_visible else "日历 (展开)")

    def emit_current_date(self):
        self.date_changed.emit(self.calendar.selectedDate().toPyDate())

    def on_calendar_changed(self):
        self.date_changed.emit(self.calendar.selectedDate().toPyDate())

    def check_system_date(self):
        today = datetime.date.today()
        if today == self.system_date:
            return
        self.system_date = today
        self.set_selected_date(today)

    def set_selected_date(self, date_value):
        if isinstance(date_value, datetime.date):
            qdate = QDate(date_value.year, date_value.month, date_value.day)
        elif isinstance(date_value, QDate):
            qdate = date_value
        else:
            return
        if self.calendar.selectedDate() == qdate:
            return
        self.calendar.setSelectedDate(qdate)
        self.emit_current_date()
