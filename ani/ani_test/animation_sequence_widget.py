from typing import List, Dict

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import QSize, pyqtSignal

from .frame_sequence_player import FrameSequencePlayer


class AnimationSequenceWidget(QWidget):
    sequence_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sequence_items: List[Dict] = []
        self.current_item_index = 0
        self.player = FrameSequencePlayer([], interval_ms=150, parent=self, loop=True)
        self.player.finished.connect(self._handle_item_finished)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.player)

    def set_sequence(self, items: List[Dict]) -> None:
        self.sequence_items = [item for item in items if item.get("frame_paths")]
        self.current_item_index = 0
        self._play_current_item()

    def _play_current_item(self) -> None:
        if not self.sequence_items:
            self.player.stop()
            return
        item = self.sequence_items[self.current_item_index]
        interval_ms = int(item.get("interval_ms", 120))
        loop = bool(item.get("loop", True))
        self.player.timer.setInterval(interval_ms)
        self.player.interval_ms = interval_ms
        self.player.set_loop(loop)
        self.player.set_frames(item.get("frame_paths", []))
        self.player.start()

    def _handle_item_finished(self) -> None:
        if not self.sequence_items:
            return
        if self.current_item_index + 1 >= len(self.sequence_items):
            self.sequence_finished.emit()
            return
        self.current_item_index += 1
        self._play_current_item()

    def get_first_frame_size(self) -> QSize:
        if self.player.pixmaps:
            return self.player.pixmaps[0].size()
        return QSize(200, 200)
