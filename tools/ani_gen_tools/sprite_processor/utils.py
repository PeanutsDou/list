"""
工具函数模块。
提供路径解析、颜色解析、文件列表等通用能力。
"""
import os
from typing import List, Tuple, Optional


def list_image_files(input_dir: str, supported_exts: Tuple[str, ...]) -> List[str]:
    """
    获取输入目录下的图片文件列表，保持原始读取顺序。
    """
    if not input_dir or not os.path.isdir(input_dir):
        return []
    files: List[str] = []
    for name in os.listdir(input_dir):
        path = os.path.join(input_dir, name)
        if not os.path.isfile(path):
            continue
        lower_name = name.lower()
        if any(lower_name.endswith(ext) for ext in supported_exts):
            files.append(path)
    return files


def ensure_output_dir(output_dir: str) -> None:
    """
    确保输出目录存在。
    """
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)


def parse_color_text(color_text: Optional[str]) -> Tuple[int, int, int]:
    """
    解析颜色字符串为 RGB 元组。
    支持格式：'255,255,255' 或 '#FFFFFF'。
    """
    if not color_text:
        return (255, 255, 255)
    text = str(color_text).strip()
    if text.startswith("#") and len(text) == 7:
        return (int(text[1:3], 16), int(text[3:5], 16), int(text[5:7], 16))
    if "," in text:
        parts = [p.strip() for p in text.split(",")]
        if len(parts) != 3:
            raise ValueError("颜色格式错误，示例：255,255,255 或 #FFFFFF")
        rgb = tuple(int(p) for p in parts)
        if any(v < 0 or v > 255 for v in rgb):
            raise ValueError("颜色通道必须在 0-255 范围内")
        return rgb  # type: ignore
    raise ValueError("颜色格式错误，示例：255,255,255 或 #FFFFFF")


def normalize_alignment(alignment: str) -> str:
    """
    归一化对齐方式。
    """
    value = (alignment or "").strip().lower()
    if value in ("bottom_center", "bottom-center", "bottom center", "底部中心对齐"):
        return "bottom_center"
    if value in ("center", "center_align", "center-align", "中心对齐"):
        return "center"
    return "bottom_center"


def normalize_remove_mode(remove_mode: str) -> str:
    """
    归一化抠图模式。
    """
    value = (remove_mode or "").strip().lower()
    if value in ("all", "remove_all", "全部剔除"):
        return "all"
    if value in ("edge", "edge_detect", "边缘检测"):
        return "edge"
    return "all"


def build_output_name(index: int, template: str) -> str:
    """
    基于模板构建输出文件名。
    """
    if not template or "{index" not in template:
        return f"frame_{index:03d}.png"
    return template.format(index=index)
