"""
动画展示层窗口。
负责在桌面上独立显示序列帧动画，并提供拖动能力。
"""
import os
import sys
import json
import random
from typing import Optional

from PyQt5.QtWidgets import QWidget, QApplication, QMenu
from PyQt5.QtCore import Qt, QPoint, QSize, QPointF, QTimer

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from ani.ani_test.egg_animation_widget import EggAnimationWidget
except Exception:
    EggAnimationWidget = None

try:
    from ani.ani_test.animation_sequence_widget import AnimationSequenceWidget
    from ani.ani_test.animation_registry import get_sequence_items, get_default_sequence_name
except Exception:
    AnimationSequenceWidget = None
    get_sequence_items = None
    get_default_sequence_name = None


class RandomSequenceController:
    def __init__(self, widget: QWidget):
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

    def update_config(self, weights: dict = None, min_seconds: float = None, max_seconds: float = None) -> None:
        if isinstance(weights, dict) and weights:
            self.sequence_weights = weights
        if isinstance(min_seconds, (int, float)) and min_seconds > 0:
            self.min_seconds = float(min_seconds)
        if isinstance(max_seconds, (int, float)) and max_seconds > 0:
            self.max_seconds = float(max_seconds)

    def start(self) -> None:
        self.switch_sequence()

    def stop(self) -> None:
        if self.timer.isActive():
            self.timer.stop()

    def switch_sequence(self) -> None:
        if get_sequence_items is None:
            return
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
        if hasattr(self.widget, "set_sequence"):
            self.widget.set_sequence(items)
        self.last_sequence = selected
        next_seconds = random.uniform(self.min_seconds, self.max_seconds)
        self.timer.start(int(next_seconds * 1000))


class AnimationLayerWindow(QWidget):
    """
    动画展示层窗口。
    独立于主 UI 启动，始终处于底层显示，但高于主 UI。
    """
    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化动画层窗口。

        Args:
            parent: 父级控件。
        """
        super().__init__(parent)
        self.drag_offset = QPoint()
        self.is_dragging = False
        self.scale_factor = 1.0
        self.min_scale = 0.1
        self.max_scale = 3.0
        self.base_size = QSize(200, 200)
        self.layer_mode = "top"
        self.state_ready = False
        self.current_sequence = None
        self.play_mode = "manual"
        self.state_signature = None
        self.random_controller = None
        self.state_timer = QTimer(self)
        self.state_timer.setInterval(1000)
        self.state_timer.timeout.connect(self.sync_state_from_file)

        self.init_window_flags()
        self.init_ui()
        self.apply_saved_state()
        self.sync_state_from_file(force=True)
        self.state_timer.start()
        self.state_ready = True

    def init_window_flags(self) -> None:
        """
        设置窗口标志，保证透明背景与底层显示。
        """
        current_geometry = self.geometry()
        is_visible = self.isVisible()
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.layer_mode == "top":
            flags |= Qt.WindowStaysOnTopHint
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setMouseTracking(True)
        if is_visible:
            self.hide()
        self.setWindowFlags(flags)
        if current_geometry.isValid():
            self.setGeometry(current_geometry)
        if is_visible:
            self.show()
        self.adjust_layer_order()

    def init_ui(self) -> None:
        """
        初始化动画展示内容。
        """
        if AnimationSequenceWidget is not None:
            self.animation_widget = AnimationSequenceWidget(self)
            self.animation_widget.setStyleSheet("background: transparent;")
            self.apply_default_animation()
        elif EggAnimationWidget is not None:
            self.animation_widget = EggAnimationWidget(self)
            self.animation_widget.setStyleSheet("background: transparent;")
        else:
            self.animation_widget = QWidget(self)
        self.resize_to_frame()

    def resize_to_frame(self) -> None:
        """
        根据首帧尺寸调整窗口大小。
        """
        if hasattr(self.animation_widget, "get_first_frame_size"):
            try:
                self.base_size = self.animation_widget.get_first_frame_size()
                self.apply_scale(self.scale_factor)
                return
            except Exception:
                pass
        if EggAnimationWidget is None or not hasattr(self.animation_widget, "player"):
            self.base_size = QSize(200, 200)
            self.apply_scale(self.scale_factor)
            return
        pixmaps = getattr(self.animation_widget.player, "pixmaps", [])
        if pixmaps:
            self.base_size = pixmaps[0].size()
            self.apply_scale(self.scale_factor)
            return
        self.base_size = QSize(200, 200)
        self.apply_scale(self.scale_factor)

    def apply_default_animation(self) -> None:
        if get_default_sequence_name is None or get_sequence_items is None:
            return
        default_name = get_default_sequence_name()
        if not default_name:
            return
        self.set_animation_by_name(default_name)

    def set_animation_by_name(self, name: str) -> None:
        if get_sequence_items is None:
            return
        if not hasattr(self.animation_widget, "set_sequence"):
            return
        items = get_sequence_items(name)
        if not items:
            return
        self.animation_widget.set_sequence(items)
        self.resize_to_frame()
        self.current_sequence = name
        if self.state_ready:
            data = self.load_animation_state()
            data["current_sequence"] = name
            if "play_mode" not in data:
                data["play_mode"] = self.play_mode
            self.save_animation_state(data)

    def apply_scale(self, scale: float) -> None:
        """
        根据缩放比例调整窗口与动画控件大小。

        Args:
            scale: 缩放倍率。
        """
        target_width = max(10, int(self.base_size.width() * scale))
        target_height = max(10, int(self.base_size.height() * scale))
        self.resize(target_width, target_height)
        self.animation_widget.resize(target_width, target_height)

    def init_position(self) -> None:
        """
        初始化动画窗口位置，默认居中显示。
        """
        screen_geo = QApplication.primaryScreen().availableGeometry()
        x = screen_geo.x() + (screen_geo.width() - self.width()) // 2
        y = screen_geo.y() + (screen_geo.height() - self.height()) // 2
        self.move(x, y)

    def adjust_layer_order(self) -> None:
        """
        根据层级模式调整显示顺序。
        """
        if self.layer_mode == "bottom":
            self.lower()
        elif self.layer_mode == "above_main":
            self.raise_()
        else:
            self.raise_()

    def load_animation_state(self) -> dict:
        """
        读取动画窗口状态数据。
        """
        state_file = os.path.join(project_root, "ani", "animation_state.json")
        if not os.path.exists(state_file):
            return {}
        try:
            with open(state_file, "r", encoding="utf-8") as file:
                data = json.load(file)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def save_animation_state(self, data: dict) -> None:
        """
        保存动画窗口状态数据。
        """
        state_file = os.path.join(project_root, "ani", "animation_state.json")
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        try:
            with open(state_file, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            pass

    def save_current_state(self) -> None:
        """
        保存当前动画窗口位置与大小等状态。
        """
        if not self.state_ready:
            return
        data = self.load_animation_state()
        data["animation_window"] = {
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height(),
            "scale": self.scale_factor,
            "layer_mode": self.layer_mode
        }
        if self.current_sequence:
            data["current_sequence"] = self.current_sequence
        data["play_mode"] = self.play_mode
        self.save_animation_state(data)

    def apply_saved_state(self) -> None:
        """
        应用上次保存的动画窗口状态。
        """
        data = self.load_animation_state()
        state = data.get("animation_window", {})
        layer_mode = state.get("layer_mode")
        if layer_mode in ("bottom", "above_main", "top"):
            self.layer_mode = layer_mode
        self.init_window_flags()

        width = state.get("width")
        height = state.get("height")
        if isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0:
            scale = None
            if self.base_size.width() > 0:
                scale = width / self.base_size.width()
            if self.base_size.height() > 0:
                height_scale = height / self.base_size.height()
                scale = height_scale if scale is None else min(scale, height_scale)
            if scale is not None:
                self.scale_factor = min(self.max_scale, max(self.min_scale, scale))
                self.apply_scale(self.scale_factor)
            else:
                self.resize(width, height)
                self.animation_widget.resize(width, height)
        else:
            self.apply_scale(self.scale_factor)

        x = state.get("x")
        y = state.get("y")
        if isinstance(x, int) and isinstance(y, int):
            self.move(x, y)
        else:
            self.init_position()
        self.adjust_layer_order()

    def _build_state_signature(self, data: dict) -> tuple:
        sequence = data.get("current_sequence")
        play_mode = data.get("play_mode")
        weights = data.get("random_weights")
        interval = data.get("random_interval")
        weights_key = json.dumps(weights, ensure_ascii=False, sort_keys=True) if isinstance(weights, dict) else None
        interval_key = json.dumps(interval, ensure_ascii=False, sort_keys=True) if isinstance(interval, dict) else None
        return (sequence, play_mode, weights_key, interval_key)

    def _ensure_random_controller(self) -> None:
        if self.random_controller is None:
            self.random_controller = RandomSequenceController(self.animation_widget)

    def _apply_play_mode(self, mode: str, data: dict) -> None:
        if mode not in ("manual", "random"):
            mode = "manual"
        self.play_mode = mode
        if mode == "random":
            self._ensure_random_controller()
            self._update_random_config(data)
            if self.random_controller:
                self.random_controller.start()
        else:
            if self.random_controller:
                self.random_controller.stop()

    def _update_random_config(self, data: dict) -> None:
        if not self.random_controller:
            return
        weights = data.get("random_weights")
        interval = data.get("random_interval")
        min_seconds = None
        max_seconds = None
        if isinstance(interval, dict):
            min_seconds = interval.get("min_seconds")
            max_seconds = interval.get("max_seconds")
        self.random_controller.update_config(weights=weights, min_seconds=min_seconds, max_seconds=max_seconds)

    def sync_state_from_file(self, force: bool = False) -> None:
        data = self.load_animation_state()
        signature = self._build_state_signature(data)
        if not force and signature == self.state_signature:
            return
        self.state_signature = signature
        play_mode = data.get("play_mode", "manual")
        if play_mode != self.play_mode:
            self._apply_play_mode(play_mode, data)
        elif self.play_mode == "random":
            self._update_random_config(data)
        if self.play_mode == "manual":
            target_sequence = data.get("current_sequence")
            if target_sequence and target_sequence != self.current_sequence:
                self.set_animation_by_name(target_sequence)
        if self.play_mode == "random" and self.random_controller and not self.random_controller.timer.isActive():
            self.random_controller.start()

    def set_layer_mode(self, mode: str) -> None:
        """
        设置动画窗口显示层级模式。
        """
        if mode not in ("bottom", "above_main", "top"):
            return
        self.layer_mode = mode
        self.init_window_flags()
        self.save_current_state()

    def mousePressEvent(self, event) -> None:
        """
        记录拖动起点。
        """
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        """
        拖动窗口到鼠标位置。
        """
        if self.is_dragging:
            self.move(event.globalPos() - self.drag_offset)
            event.accept()

    def wheelEvent(self, event) -> None:
        """
        滚轮缩放动画展示内容。
        """
        delta = event.angleDelta().y()
        if delta == 0:
            event.ignore()
            return
        step = 0.1 if delta > 0 else -0.1
        old_size = self.size()
        old_width = old_size.width()
        old_height = old_size.height()
        if old_width > 0 and old_height > 0:
            anchor_ratio = QPointF(event.pos().x() / old_width, event.pos().y() / old_height)
        else:
            anchor_ratio = QPointF(0.5, 0.5)
        new_scale = min(self.max_scale, max(self.min_scale, self.scale_factor + step))
        if new_scale != self.scale_factor:
            anchor_global = self.mapToGlobal(event.pos())
            self.scale_factor = new_scale
            target_width = max(10, int(self.base_size.width() * new_scale))
            target_height = max(10, int(self.base_size.height() * new_scale))
            anchor_offset = QPoint(int(anchor_ratio.x() * target_width), int(anchor_ratio.y() * target_height))
            new_top_left = anchor_global - anchor_offset
            self.setUpdatesEnabled(False)
            self.setGeometry(new_top_left.x(), new_top_left.y(), target_width, target_height)
            self.animation_widget.setGeometry(0, 0, target_width, target_height)
            self.setUpdatesEnabled(True)
            self.update()
            self.save_current_state()
        event.accept()

    def showEvent(self, event) -> None:
        """
        显示时提升到主 UI 上方的底层顺序。
        """
        super().showEvent(event)
        self.adjust_layer_order()

    def moveEvent(self, event) -> None:
        """
        位置变化时记录窗口状态。
        """
        super().moveEvent(event)
        self.save_current_state()

    def resizeEvent(self, event) -> None:
        """
        尺寸变化时记录窗口状态。
        """
        super().resizeEvent(event)
        self.save_current_state()

    def mouseReleaseEvent(self, event) -> None:
        """
        结束拖动。
        """
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            self.save_current_state()
            event.accept()

    def contextMenuEvent(self, event) -> None:
        """
        右键菜单设置显示层级。
        """
        if not self.animation_widget.geometry().contains(event.pos()):
            event.ignore()
            return
        menu = QMenu(self)
        bottom_action = menu.addAction("置于底层")
        above_main_action = menu.addAction("高于主ui界面，低于其他窗口")
        top_action = menu.addAction("置顶")

        bottom_action.setCheckable(True)
        above_main_action.setCheckable(True)
        top_action.setCheckable(True)
        bottom_action.setChecked(self.layer_mode == "bottom")
        above_main_action.setChecked(self.layer_mode == "above_main")
        top_action.setChecked(self.layer_mode == "top")

        selected = menu.exec_(event.globalPos())
        if selected == bottom_action:
            self.set_layer_mode("bottom")
        elif selected == above_main_action:
            self.set_layer_mode("above_main")
        elif selected == top_action:
            self.set_layer_mode("top")
