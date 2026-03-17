from __future__ import annotations

import argparse
import sys
from typing import Sequence
from datetime import datetime

from .search import iter_search_results


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

    results = iter_search_results(
        roots=args.roots,
        pattern=args.pattern,
        ignore_patterns=args.ignore,
    )

    found_any = False
    for item in results:
        # 找到任何结果时设置标志为 True
        found_any = True
        # 简单文本输出：路径 | 大小(字节) | 修改时间（人类可读的时间）
        human_readable_mtime = datetime.fromtimestamp(item.mtime).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        print(f"{item.path} | {item.size} bytes | mtime={human_readable_mtime}")
    if not found_any:
        # 没找到任何结果时给个提示
        print("No matching files found.", file=sys.stderr)

    return 0
