"""
序列帧动画播放器模块。
提供一个可复用的 QWidget，用于循环播放本地图片序列帧。
"""
from typing import List, Optional
import os

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap


class FrameSequencePlayer(QWidget):
    """
    序列帧动画播放器。
    使用 QTimer 定时切换帧图片，实现循环播放效果。
    """
    finished = pyqtSignal()

    def __init__(self, frame_paths: Optional[List[str]] = None, interval_ms: int = 120,
                 parent: Optional[QWidget] = None, loop: bool = True):
        """
        初始化播放器。

        Args:
            frame_paths: 初始帧路径列表。
            interval_ms: 帧切换间隔（毫秒）。
            parent: 父级控件。
        """
        super().__init__(parent)
        self.frame_paths: List[str] = []
        self.pixmaps: List[QPixmap] = []
        self.current_index = 0
        self.interval_ms = interval_ms
        self.loop = loop

        self.timer = QTimer(self)
        self.timer.setInterval(self.interval_ms)
        self.timer.timeout.connect(self._next_frame)

        self.display_label = QLabel("")
        self.display_label.setAlignment(Qt.AlignCenter)
        self.display_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.display_label.setStyleSheet("background: transparent;")
        self.setAttribute(Qt.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.display_label)

        if frame_paths:
            self.set_frames(frame_paths)
        self.start()

    def set_frames(self, frame_paths: List[str]) -> None:
        """
        设置并加载新的帧列表。

        Args:
            frame_paths: 帧图片的完整路径列表。
        """
        self.frame_paths = [p for p in frame_paths if isinstance(p, str) and os.path.exists(p)]
        self.pixmaps = [QPixmap(path) for path in self.frame_paths if QPixmap(path).isNull() is False]
        self.current_index = 0
        self._render_current_frame()

    def start(self) -> None:
        """
        启动动画播放。
        """
        if not self.timer.isActive():
            self.timer.start()

    def stop(self) -> None:
        """
        停止动画播放。
        """
        if self.timer.isActive():
            self.timer.stop()

    def set_loop(self, loop: bool) -> None:
        self.loop = bool(loop)

    def _next_frame(self) -> None:
        """
        切换到下一帧。
        """
        if not self.pixmaps:
            self.display_label.setText("")
            return
        if not self.loop and self.current_index >= len(self.pixmaps) - 1:
            self.stop()
            self.finished.emit()
            return
        self.current_index = (self.current_index + 1) % len(self.pixmaps)
        self._render_current_frame()

    def _render_current_frame(self) -> None:
        """
        渲染当前帧到显示区域，并按控件尺寸等比缩放。
        """
        if not self.pixmaps:
            self.display_label.setText("")
            self.display_label.setPixmap(QPixmap())
            return
        current_pixmap = self.pixmaps[self.current_index]
        target_size = self.display_label.size()
        if target_size.width() <= 1 or target_size.height() <= 1:
            self.display_label.setPixmap(current_pixmap)
            return
        scaled = current_pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.display_label.setPixmap(scaled)

    def resizeEvent(self, event) -> None:
        """
        监听控件尺寸变化，保持当前帧自适应显示。
        """
        super().resizeEvent(event)
        self._render_current_frame()
