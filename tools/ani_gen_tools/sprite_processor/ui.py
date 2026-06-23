"""
可视化界面模块。
提供路径选择、阈值设置、对齐方式与进度展示。
"""
import os
import sys
from typing import Optional, Dict

from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QComboBox,
    QSlider,
    QProgressBar,
    QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

try:
    from .config import SpriteProcessorConfig
    from .processor import SpriteProcessor
except Exception:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.append(current_dir)
    from config import SpriteProcessorConfig
    from processor import SpriteProcessor


class ProcessorWorker(QThread):
    """
    后台处理线程，避免阻塞 UI。
    """
    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)
    finished_signal = pyqtSignal(dict)

    def __init__(self, config: SpriteProcessorConfig) -> None:
        super().__init__()
        self.config = config

    def run(self) -> None:
        processor = SpriteProcessor(self.config)
        total_holder = {"total": 1}

        def on_progress(current: int, total: int) -> None:
            total_holder["total"] = total
            value = int(current / total * 100) if total > 0 else 0
            self.progress_changed.emit(value)

        def on_status(text: str) -> None:
            self.status_changed.emit(text)

        result = processor.process(progress_callback=on_progress, status_callback=on_status)
        self.finished_signal.emit(result)


class SpriteProcessorUI(QWidget):
    """
    精灵序列帧处理工具界面。
    """
    def __init__(self) -> None:
        super().__init__()
        self.worker: Optional[ProcessorWorker] = None
        self.init_ui()

    def init_ui(self) -> None:
        """
        初始化界面布局与控件。
        """
        self.setWindowTitle("精灵序列图自动处理工具")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)

        self.input_path_edit = QLineEdit()
        self.output_path_edit = QLineEdit()

        input_layout = self._build_path_row("输入文件夹：", self.input_path_edit, self.choose_input_dir)
        output_layout = self._build_path_row("输出文件夹：", self.output_path_edit, self.choose_output_dir)

        layout.addLayout(input_layout)
        layout.addLayout(output_layout)

        align_layout = QHBoxLayout()
        align_label = QLabel("对齐方式：")
        self.align_combo = QComboBox()
        self.align_combo.addItems(["底部中心对齐", "中心对齐"])
        align_layout.addWidget(align_label)
        align_layout.addWidget(self.align_combo)
        layout.addLayout(align_layout)

        remove_layout = QHBoxLayout()
        remove_label = QLabel("抠图模式：")
        self.remove_combo = QComboBox()
        self.remove_combo.addItems(["全部剔除", "边缘检测"])
        remove_layout.addWidget(remove_label)
        remove_layout.addWidget(self.remove_combo)
        layout.addLayout(remove_layout)

        threshold_layout = QHBoxLayout()
        threshold_label = QLabel("白色阈值：")
        self.threshold_value_label = QLabel("250")
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(0, 255)
        self.threshold_slider.setValue(250)
        self.threshold_slider.valueChanged.connect(self.update_threshold_label)
        threshold_layout.addWidget(threshold_label)
        threshold_layout.addWidget(self.threshold_slider)
        threshold_layout.addWidget(self.threshold_value_label)
        layout.addLayout(threshold_layout)

        self.start_button = QPushButton("开始处理")
        self.start_button.clicked.connect(self.start_processing)
        layout.addWidget(self.start_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("等待开始")
        layout.addWidget(self.status_label)

    def _build_path_row(self, title: str, line_edit: QLineEdit, callback) -> QHBoxLayout:
        """
        构建路径输入行布局。
        """
        layout = QHBoxLayout()
        label = QLabel(title)
        button = QPushButton("选择")
        button.clicked.connect(callback)
        layout.addWidget(label)
        layout.addWidget(line_edit)
        layout.addWidget(button)
        return layout

    def choose_input_dir(self) -> None:
        """
        选择输入目录。
        """
        path = QFileDialog.getExistingDirectory(self, "选择输入文件夹")
        if path:
            self.input_path_edit.setText(path)

    def choose_output_dir(self) -> None:
        """
        选择输出目录。
        """
        path = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if path:
            self.output_path_edit.setText(path)

    def update_threshold_label(self, value: int) -> None:
        """
        更新阈值显示。
        """
        self.threshold_value_label.setText(str(value))

    def start_processing(self) -> None:
        """
        启动后台处理任务。
        """
        input_dir = self.input_path_edit.text().strip()
        output_dir = self.output_path_edit.text().strip()
        if not input_dir or not os.path.isdir(input_dir):
            QMessageBox.warning(self, "提示", "请输入有效的输入文件夹路径")
            return
        if not output_dir:
            QMessageBox.warning(self, "提示", "请输入输出文件夹路径")
            return

        alignment = "bottom_center" if self.align_combo.currentIndex() == 0 else "center"
        remove_mode = "all" if self.remove_combo.currentIndex() == 0 else "edge"
        threshold = self.threshold_slider.value()

        config = SpriteProcessorConfig(
            input_dir=input_dir,
            output_dir=output_dir,
            alignment=alignment,
            white_threshold=threshold,
            remove_mode=remove_mode
        )

        self.start_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("开始处理...")

        self.worker = ProcessorWorker(config)
        self.worker.progress_changed.connect(self.progress_bar.setValue)
        self.worker.status_changed.connect(self.status_label.setText)
        self.worker.finished_signal.connect(self.handle_finished)
        self.worker.start()

    def handle_finished(self, result: Dict) -> None:
        """
        处理完成后的收尾逻辑。
        """
        self.start_button.setEnabled(True)
        if result.get("success"):
            self.progress_bar.setValue(100)
            self.status_label.setText(f"处理完成，输出：{result.get('output_dir')}")
        else:
            self.status_label.setText(f"处理失败：{result.get('message')}")
            QMessageBox.warning(self, "处理失败", result.get("message", "未知错误"))


def main() -> None:
    """
    UI 独立运行入口。
    """
    app = QApplication(sys.argv)
    window = SpriteProcessorUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
