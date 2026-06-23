"""
核心处理逻辑模块。
负责抠白、裁剪、对齐与批量输出。
"""
from typing import Callable, Dict, List, Optional, Tuple
import os
import sys

from PIL import Image

try:
    from .config import SpriteProcessorConfig
    from .utils import list_image_files, ensure_output_dir, build_output_name, normalize_alignment, normalize_remove_mode
except Exception:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.append(current_dir)
    from config import SpriteProcessorConfig
    from utils import list_image_files, ensure_output_dir, build_output_name, normalize_alignment, normalize_remove_mode


ProgressCallback = Callable[[int, int], None]
StatusCallback = Callable[[str], None]


class SpriteProcessor:
    """
    精灵序列帧处理器。
    """
    def __init__(self, config: SpriteProcessorConfig) -> None:
        self.config = config
        self.config.alignment = normalize_alignment(self.config.alignment)
        self.config.remove_mode = normalize_remove_mode(self.config.remove_mode)

    def process(
        self,
        progress_callback: Optional[ProgressCallback] = None,
        status_callback: Optional[StatusCallback] = None
    ) -> Dict:
        """
        执行批量处理并输出 PNG 序列帧。
        """
        files = list_image_files(self.config.input_dir, self.config.supported_exts)
        if not files:
            return {
                "success": False,
                "reason": "no_files",
                "message": "输入目录未找到可处理的图片文件",
                "processed": 0,
                "skipped": 0,
                "errors": []
            }

        ensure_output_dir(self.config.output_dir)

        processed_images: List[Image.Image] = []
        errors: List[str] = []

        total = len(files)
        for index, path in enumerate(files, start=1):
            if status_callback:
                status_callback(f"处理图片：{os.path.basename(path)}")
            try:
                image = Image.open(path).convert("RGBA")
                image = self._remove_background(image)
                cropped = self._auto_crop(image)
                processed_images.append(cropped)
            except Exception as exc:
                errors.append(f"{path}: {exc}")
            if progress_callback:
                progress_callback(index, total)

        if not processed_images:
            return {
                "success": False,
                "reason": "all_failed",
                "message": "全部图片处理失败",
                "processed": 0,
                "skipped": total,
                "errors": errors
            }

        max_width, max_height = self._get_max_size(processed_images)
        saved_count = 0
        for index, image in enumerate(processed_images, start=1):
            aligned = self._align_to_canvas(image, max_width, max_height)
            output_name = build_output_name(index, self.config.name_template)
            output_path = os.path.join(self.config.output_dir, output_name)
            aligned.save(output_path, format="PNG")
            saved_count += 1

        return {
            "success": True,
            "processed": saved_count,
            "skipped": total - saved_count,
            "errors": errors,
            "output_dir": self.config.output_dir,
            "max_size": (max_width, max_height)
        }

    def _remove_background(self, image: Image.Image) -> Image.Image:
        """
        将背景色转换为透明通道。
        """
        if self.config.remove_mode == "edge":
            return self._remove_background_edge(image)
        return self._remove_background_all(image)

    def _remove_background_all(self, image: Image.Image) -> Image.Image:
        """
        全量剔除背景色模式。
        """
        bg_r, bg_g, bg_b = self.config.background_color
        threshold = self.config.white_threshold
        data = list(image.getdata())
        new_data = []

        if self.config.background_color == (255, 255, 255):
            for r, g, b, a in data:
                if r >= threshold and g >= threshold and b >= threshold:
                    new_data.append((r, g, b, 0))
                else:
                    new_data.append((r, g, b, a))
        else:
            tolerance = max(0, 255 - threshold)
            for r, g, b, a in data:
                if (
                    abs(r - bg_r) <= tolerance
                    and abs(g - bg_g) <= tolerance
                    and abs(b - bg_b) <= tolerance
                ):
                    new_data.append((r, g, b, 0))
                else:
                    new_data.append((r, g, b, a))

        image.putdata(new_data)
        return image

    def _remove_background_edge(self, image: Image.Image) -> Image.Image:
        """
        边缘检测模式：仅剔除外轮廓以外的背景色。
        """
        bg_r, bg_g, bg_b = self.config.background_color
        threshold = self.config.white_threshold
        outline_threshold = 60
        width, height = image.size
        data = list(image.getdata())
        total = width * height
        candidates = [False] * total
        outlines = [False] * total

        def is_candidate(r: int, g: int, b: int) -> bool:
            if self.config.background_color == (255, 255, 255):
                return r >= threshold and g >= threshold and b >= threshold
            tolerance = max(0, 255 - threshold)
            return (
                abs(r - bg_r) <= tolerance
                and abs(g - bg_g) <= tolerance
                and abs(b - bg_b) <= tolerance
            )

        def is_outline(r: int, g: int, b: int) -> bool:
            return r <= outline_threshold and g <= outline_threshold and b <= outline_threshold

        for idx, (r, g, b, _a) in enumerate(data):
            if is_candidate(r, g, b):
                candidates[idx] = True
            if is_outline(r, g, b):
                outlines[idx] = True

        visited = [False] * total
        queue: List[int] = []

        def push_index(i: int) -> None:
            if not candidates[i] or outlines[i] or visited[i]:
                return
            visited[i] = True
            queue.append(i)

        for x in range(width):
            push_index(x)
            push_index((height - 1) * width + x)
        for y in range(height):
            push_index(y * width)
            push_index(y * width + (width - 1))

        cursor = 0
        while cursor < len(queue):
            idx = queue[cursor]
            cursor += 1
            x = idx % width
            y = idx // width
            if x > 0:
                push_index(idx - 1)
            if x < width - 1:
                push_index(idx + 1)
            if y > 0:
                push_index(idx - width)
            if y < height - 1:
                push_index(idx + width)

        new_data = []
        for idx, (r, g, b, a) in enumerate(data):
            if candidates[idx] and visited[idx]:
                new_data.append((r, g, b, 0))
            else:
                new_data.append((r, g, b, a))

        image.putdata(new_data)
        return image

    def _auto_crop(self, image: Image.Image) -> Image.Image:
        """
        自动裁剪到最小非透明区域。
        """
        alpha = image.split()[-1]
        bbox = alpha.getbbox()
        if not bbox:
            return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        return image.crop(bbox)

    def _get_max_size(self, images: List[Image.Image]) -> Tuple[int, int]:
        """
        获取序列帧中最大的宽高。
        """
        widths = [img.width for img in images]
        heights = [img.height for img in images]
        return max(widths), max(heights)

    def _align_to_canvas(self, image: Image.Image, max_width: int, max_height: int) -> Image.Image:
        """
        按配置对齐方式将图像贴到统一画布上。
        """
        canvas = Image.new("RGBA", (max_width, max_height), (0, 0, 0, 0))
        if self.config.alignment == "center":
            x = (max_width - image.width) // 2
            y = (max_height - image.height) // 2
        else:
            x = (max_width - image.width) // 2
            y = max_height - image.height
        canvas.paste(image, (x, y), image)
        return canvas
