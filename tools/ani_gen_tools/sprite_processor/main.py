"""
主程序入口（命令行模式）。
支持传入参数并执行批量处理。
"""
import argparse
import os
import sys

try:
    from .config import SpriteProcessorConfig
    from .processor import SpriteProcessor
    from .utils import parse_color_text, normalize_alignment, normalize_remove_mode
except Exception:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.append(current_dir)
    from config import SpriteProcessorConfig
    from processor import SpriteProcessor
    from utils import parse_color_text, normalize_alignment, normalize_remove_mode


def build_parser() -> argparse.ArgumentParser:
    """
    构建命令行参数解析器。
    """
    parser = argparse.ArgumentParser(description="精灵序列帧自动处理工具")
    parser.add_argument("--input", required=True, help="输入文件夹路径")
    parser.add_argument("--output", required=False, help="输出文件夹路径")
    parser.add_argument("--alignment", default="bottom_center", help="对齐方式：bottom_center 或 center")
    parser.add_argument("--threshold", type=int, default=250, help="白色阈值（0-255）")
    parser.add_argument("--bg-color", default=None, help="背景色，格式 255,255,255 或 #FFFFFF")
    parser.add_argument("--name-template", default="frame_{index:03d}.png", help="输出命名模板")
    parser.add_argument("--remove-mode", default="all", help="抠图模式：all 或 edge")
    return parser


def resolve_output_dir(input_dir: str, output_dir: str) -> str:
    """
    解析输出目录，必要时询问用户输入。
    """
    if output_dir:
        return output_dir
    folder_name = input("请输入输出文件夹名称：").strip()
    if not folder_name:
        raise ValueError("输出文件夹名称不能为空")
    return os.path.join(input_dir, folder_name)


def main() -> None:
    """
    命令行入口函数。
    """
    parser = build_parser()
    args = parser.parse_args()

    input_dir = os.path.abspath(args.input)
    output_dir = resolve_output_dir(input_dir, args.output)
    alignment = normalize_alignment(args.alignment)
    remove_mode = normalize_remove_mode(args.remove_mode)
    if args.threshold < 0 or args.threshold > 255:
        raise ValueError("白色阈值必须在 0-255 范围内")
    bg_color = parse_color_text(args.bg_color)

    config = SpriteProcessorConfig(
        input_dir=input_dir,
        output_dir=output_dir,
        alignment=alignment,
        white_threshold=args.threshold,
        background_color=bg_color,
        name_template=args.name_template,
        remove_mode=remove_mode
    )
    processor = SpriteProcessor(config)
    result = processor.process()
    if not result.get("success"):
        print(f"处理失败：{result.get('message')}")
        if result.get("errors"):
            print("错误详情：")
            for item in result["errors"]:
                print(f"- {item}")
        sys.exit(1)

    print("处理完成")
    print(f"输出目录：{result.get('output_dir')}")
    print(f"处理数量：{result.get('processed')}")
    if result.get("errors"):
        print(f"失败数量：{len(result.get('errors'))}")


if __name__ == "__main__":
    main()
