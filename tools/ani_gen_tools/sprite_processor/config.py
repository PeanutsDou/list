"""
配置模块。
集中管理处理参数，便于命令行与界面共享。
"""
from dataclasses import dataclass
from typing import Tuple


@dataclass
class SpriteProcessorConfig:
    """
    精灵序列处理配置。
    """
    input_dir: str
    output_dir: str
    alignment: str = "bottom_center"
    white_threshold: int = 250
    background_color: Tuple[int, int, int] = (255, 255, 255)
    remove_mode: str = "all"
    name_template: str = "frame_{index:03d}.png"
    supported_exts: Tuple[str, ...] = (".png", ".jpg", ".jpeg")
