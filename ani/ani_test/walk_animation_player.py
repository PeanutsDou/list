import sys
import os

from PyQt5.QtWidgets import QApplication

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from ani.ani_test.animation_sequence_widget import AnimationSequenceWidget
from ani.ani_test.animation_registry import get_sequence_items


def main() -> None:
    app = QApplication(sys.argv)
    widget = AnimationSequenceWidget()
    items = get_sequence_items("walk")
    if items:
        widget.set_sequence(items)
    widget.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
