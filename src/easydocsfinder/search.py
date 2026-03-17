from __future__ import annotations  # 允许延迟解析类型注解

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterator, Sequence


# 创建一个数据类来表示搜索结果
@dataclass(frozen=True)
class SearchResult:
    path: Path  # 文件的绝对路径
    size: int  # 文件的大小(字节)
    mtime: float  # 文件的最后修改时间(时间戳)


def _name_matches_any(name: str, patterns: Sequence[str]) -> bool:
    for pattern in patterns:
        # 通过 fnmatch 函数检查文件名是否匹配忽略模式
        # fnmatch 函数是 Python 标准库中的一个函数，用于匹配文件名
        # 它使用通配符模式来匹配文件名
        if fnmatch(name, pattern):
            return True
    return False


def _walk_path(
    root: Path,
    pattern: str,
    ignore_patterns: Sequence[str],
) -> Iterator[SearchResult]:
    for entry in root.iterdir():
        # 列出根目录下的所有文件和目录，不递归
        if entry.is_dir():
            # 目录名命中忽略规则：剪枝，不再递归
            if _name_matches_any(entry.name, ignore_patterns):
                continue
            # 否则递归进入子目录，通过yield from把子目录的搜索结果传递给父级
            yield from _walk_path(entry, pattern, ignore_patterns)
        elif entry.is_file():
            # 先按 pattern 过滤
            if not fnmatch(entry.name, pattern):
                continue
            # 再按 ignore_patterns 过滤文件名
            if _name_matches_any(entry.name, ignore_patterns):
                continue
            stat = entry.stat()
            yield SearchResult(
                path=entry.resolve(),
                size=stat.st_size,
                mtime=stat.st_mtime,
            )


def iter_search_results(
    roots: Sequence[str | Path],
    pattern: str = "*",
    ignore_patterns: Sequence[str] | None = None,
) -> Iterator[SearchResult]:
    """
    串行遍历 roots 下的所有文件，按 pattern 过滤，并按 ignore_patterns 忽略。
    """
    if ignore_patterns is None:
        # 注意默认值为 None，需要显式转换为空列表
        ignore_patterns = []

    for root in roots:
        # 遍历要搜索的根目录，首先转换为 Path 对象
        root_path = Path(root)
        # 如果该目录不存在或不是目录，则跳过
        if not root_path.exists() or not root_path.is_dir():
            continue
        # 递归遍历该目录下的所有文件和目录，通过yield from把子目录的搜索结果传递给父级
        yield from _walk_path(root_path, pattern, ignore_patterns)


def search(
    roots: Sequence[str | Path],
    pattern: str = "*",
    ignore_patterns: Sequence[str] | None = None,
) -> list[SearchResult]:
    """
    一次性拿到全部结果的封装列表。
    Args:
        roots: 要搜索的根目录列表
        pattern: 文件名模式
        ignore_patterns: 忽略模式列表
    Returns:
        SearchResult 对象列表
    """
    return list(
        iter_search_results(roots, pattern=pattern, ignore_patterns=ignore_patterns)
    )
