import argparse
import sys
from typing import Sequence


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="easydocsfinder", description="Fast local file search tool."
    )

    # 添加必要的位置参数：指定要搜索的根目录
    parser.add_argument(
        "roots",
        nargs="+",
        help="One or more root directories to search.",
    )

    # 添加可选参数：指定要搜索的文件名模式
    parser.add_argument(
        "-p",
        "--pattern",
        default="*",
        help="Glob pattern for file names, e.g. *.py, *.txt. Default: *",
    )

    # 添加可选参数：指定要忽略的文件名模式
    parser.add_argument(
        "-i",
        "--ignore",
        action="append",
        default=[],
        help="Glob pattern to ignore (can be used multiple times).",
    )

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    args = parse_args(argv)

    # 打印解析结果，用于测试
    print(f"roots   : {args.roots}")
    print(f"pattern : {args.pattern}")
    print(f"ignore  : {args.ignore}")

    return 0
