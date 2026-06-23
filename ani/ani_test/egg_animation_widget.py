"""
蛋序列帧动画组件。
负责定位素材路径、构建帧列表，并组合序列帧播放器。
"""
from typing import List, Optional
import os
import sys

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt

try:
    from .frame_sequence_player import FrameSequencePlayer
except Exception:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    project_root = os.path.dirname(parent_dir)
    if project_root not in sys.path:
        sys.path.append(project_root)
    from ani.ani_test.frame_sequence_player import FrameSequencePlayer


def build_egg_frame_paths() -> List[str]:
    """
    构建蛋动画序列帧的完整路径列表。

    Returns:
        帧文件路径列表，按蛋01-蛋06的顺序排列。
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    frames_dir = os.path.join(project_root, "ani", "蛋动画")
    frame_names = [f"蛋{index:02d}.png" for index in range(1, 34)]
    return [os.path.join(frames_dir, name) for name in frame_names]


def export_egg_animation_gif(output_path: Optional[str] = None,
                             max_side: int = 400,
                             frame_step: int = 2,
                             interval_ms: int = 300) -> Optional[str]:
    frame_paths = [path for path in build_egg_frame_paths() if os.path.exists(path)]
    if not frame_paths:
        return None
    if frame_step < 1:
        frame_step = 1
    frames = frame_paths[::frame_step]
    if output_path is None:
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "egg_animation.gif")
    try:
        from PIL import Image
    except Exception:
        return None

    pil_frames = []
    for frame_path in frames:
        try:
            image = Image.open(frame_path).convert("RGBA")
        except Exception:
            continue
        if max_side and max_side > 0:
            image.thumbnail((max_side, max_side), Image.LANCZOS)
        image = image.convert("P", palette=Image.ADAPTIVE, colors=128)
        pil_frames.append(image)

    if not pil_frames:
        return None

    pil_frames[0].save(
        output_path,
        save_all=True,
        append_images=pil_frames[1:],
        duration=interval_ms,
        loop=0,
        optimize=True
    )
    return output_path


class EggAnimationWidget(QWidget):
    """
    蛋序列帧动画展示控件。
    内部封装 FrameSequencePlayer，并提供基础样式更新能力。
    """
    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化蛋动画控件。

        Args:
            parent: 父级控件。
        """
        super().__init__(parent)
        self.text_color = "white"
        self.border_color = "rgba(255, 255, 255, 50)"
        self.is_light = False

        self.player = FrameSequencePlayer(build_egg_frame_paths(), interval_ms=150, parent=self)
        self.player.display_label.setText("")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.player)

        self.update_style(self.text_color, self.border_color, self.is_light)

    def update_style(self, text_color: str, border_color: str, is_light_theme: bool) -> None:
        """
        更新控件样式，保持与主界面风格一致。

        Args:
            text_color: 文本颜色。
            border_color: 边框颜色。
            is_light_theme: 是否为浅色主题。
        """
        self.text_color = text_color
        self.border_color = border_color
        self.is_light = is_light_theme
        self.player.display_label.setStyleSheet(f"color: {text_color}; background: transparent;")


if __name__ == "__main__":
    result_path = export_egg_animation_gif()
    if result_path:
        print(f"GIF 已输出：{result_path}")
    else:
        print("GIF 输出失败")
