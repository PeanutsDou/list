import os
import sys
import random

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from ani.ani_test.animation_sequence_widget import AnimationSequenceWidget
from ani.ani_test.animation_registry import get_sequence_items


class RandomSequenceController:
    def __init__(self, widget: AnimationSequenceWidget) -> None:
        self.widget = widget
        self.sequence_weights = {
            "sleep_series": 0.6,
            "takeoff_hover": 0.4
        }
        self.min_seconds = 6
        self.max_seconds = 14
        self.timer = QTimer(widget)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.switch_sequence)
        self.last_sequence = None

    def start(self) -> None:
        self.switch_sequence()

    def switch_sequence(self) -> None:
        available = {}
        for name, weight in self.sequence_weights.items():
            items = get_sequence_items(name)
            if items:
                available[name] = (weight, items)
        if not available:
            return
        names = list(available.keys())
        weights = [available[name][0] for name in names]
        selected = random.choices(names, weights=weights, k=1)[0]
        if self.last_sequence and len(names) > 1 and selected == self.last_sequence:
            candidates = [name for name in names if name != self.last_sequence]
            candidate_weights = [available[name][0] for name in candidates]
            selected = random.choices(candidates, weights=candidate_weights, k=1)[0]
        items = available[selected][1]
        self.widget.set_sequence(items)
        self.last_sequence = selected
        next_seconds = random.uniform(self.min_seconds, self.max_seconds)
        self.timer.start(int(next_seconds * 1000))


def main() -> None:
    app = QApplication(sys.argv)
    widget = AnimationSequenceWidget()
    controller = RandomSequenceController(widget)
    controller.start()
    widget.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
