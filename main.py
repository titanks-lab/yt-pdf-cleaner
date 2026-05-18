#!/usr/bin/env python3
"""YT-PDFCleaner — PDF Watermark Removal Tool.

Entry point for the application. Supports both GUI and CLI modes.

Usage:
    python main.py           # Launch GUI
    python main.py --cli     # CLI mode for batch processing
    python main.py --help    # Show help
"""

import argparse
import os
import sys
import json


def main() -> None:
    """Main entry point — parse args and launch appropriate interface."""
    parser = argparse.ArgumentParser(
        description="YT-PDFCleaner — PDF 水印清除工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python main.py                    # 启动图形界面\n"
            "  python main.py --cli input.pdf    # CLI 模式处理单个文件\n"
            "  python main.py --cli --dir ./pdfs # CLI 模式批量处理文件夹\n"
        ),
    )

    parser.add_argument(
        "--cli",
        action="store_true",
        help="以命令行模式运行（无需 GUI）",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="输入 PDF 文件路径（CLI 模式）",
    )
    parser.add_argument(
        "--dir",
        type=str,
        default=None,
        help="输入文件夹路径（CLI 模式，批量扫描）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出目录（CLI 模式，默认: 输入文件同目录/YT_output）",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["pdf", "markdown"],
        default="pdf",
        help="处理模式: pdf（去水印）或 markdown（转文本）",
    )
    parser.add_argument(
        "--theme",
        type=str,
        default="superhero",
        help="GUI 主题 (ttkbootstrap): superhero, darkly, cyborg, journal 等",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本号",
    )

    args = parser.parse_args()

    # Version
    if args.version:
        print("YT-PDFCleaner v1.3.0")
        print("PDF Watermark Removal Tool")
        sys.exit(0)

    # CLI mode
    if args.cli:
        _run_cli(args)
        return

    # GUI mode (default)
    _run_gui(args)


def _run_gui(args: argparse.Namespace) -> None:
    """Launch the GUI application."""
    try:
        import ttkbootstrap
    except ImportError:
        print("错误: 需要 ttkbootstrap 库。请运行: pip install ttkbootstrap")
        sys.exit(1)

    try:
        from gui.app import YTPDFCleanerApp
    except ImportError as exc:
        print(f"错误: 无法加载 GUI 模块: {exc}")
        print("请确保在项目根目录运行此脚本。")
        sys.exit(1)

    # Override theme if specified
    if args.theme:
        import ttkbootstrap as tb
        # We'll pass the theme via an env var for the app to pick up
        os.environ["YT_THEME"] = args.theme

    app = YTPDFCleanerApp()
    app.mainloop()


def _run_cli(args: argparse.Namespace) -> None:
    """Run in CLI mode — batch processing without GUI."""
    try:
        from core.engine import detect_watermark, remove_watermark, convert_to_markdown
        from core.scanner import scan_directory, batch_process
    except ImportError as exc:
        print(f"错误: 无法加载核心引擎: {exc}")
        print("请确保在项目根目录运行此脚本。")
        sys.exit(1)

    files_to_process = []

    if args.dir:
        # Scan directory
        print(f"扫描文件夹: {args.dir}")
        results = scan_directory(args.dir)
        files_to_process = [r["path"] for r in results if "error" not in r]
        print(f"找到 {len(files_to_process)} 个 PDF 文件")

        if not files_to_process:
            print("没有找到可处理的 PDF 文件。")
            sys.exit(0)

    elif args.input:
        # Single file
        if not os.path.isfile(args.input):
            print(f"错误: 文件不存在: {args.input}")
            sys.exit(1)
        files_to_process = [os.path.abspath(args.input)]

    else:
        print("CLI 模式需要指定输入文件或文件夹。")
        print("使用: python main.py --cli <file.pdf>")
        print("  或: python main.py --cli --dir <folder>")
        sys.exit(1)

    # Determine output dir
    if args.output:
        output_dir = args.output
    else:
        base = os.path.dirname(files_to_process[0])
        output_dir = os.path.join(base, "YT_output")

    os.makedirs(output_dir, exist_ok=True)

    print(f"\nYT-PDFCleaner — CLI 模式")
    print(f"{'=' * 50}")
    print(f"模式: {'PDF 去水印' if args.mode == 'pdf' else 'Markdown 转换'}")
    print(f"文件数: {len(files_to_process)}")
    print(f"输出目录: {output_dir}")
    print()

    # Process
    results = batch_process(files_to_process, output_dir, mode=args.mode)

    # Summary
    success = sum(1 for r in results if r.get("success"))
    failed = sum(1 for r in results if not r.get("success"))

    print(f"\n{'=' * 50}")
    print(f"处理完成: {success} 成功, {failed} 失败")

    for r in results:
        name = os.path.basename(r.get("_source", "?"))
        if r.get("success"):
            print(f"  ✅ {name} → {r.get('_output', '?')}")
        else:
            print(f"  ❌ {name} — {r.get('error', '未知错误')}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
