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


def _should_ignore(path: Path, ignore_patterns: Sequence[str]) -> bool:
    """
    检查文件是否应该被忽略
    Args:
        path: 文件的绝对路径
        ignore_patterns: 忽略模式列表
    Returns:
        True 如果文件应该被忽略, False 如果文件不应该被忽略
    """
    name = path.name
    for pattern in ignore_patterns:
        # 通过 fnmatch 函数检查文件名是否匹配忽略模式
        # fnmatch 函数是 Python 标准库中的一个函数，用于匹配文件名
        # 它使用通配符模式来匹配文件名
        if fnmatch(name, pattern):
            return True
    return False


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
        if not root_path.exists():
            # 如果该目录不存在，则跳过
            continue
        if not root_path.is_dir():
            # 如果该路径不是目录，则跳过
            continue

        for entry in root_path.rglob("*"):
            # 递归遍历得到该路径下的所有文件路径
            if not entry.is_file():
                # 如果该路径不是文件，则跳过
                continue

            if not fnmatch(entry.name, pattern):
                # 如果该文件名不符合 pattern 过滤条件，则跳过
                continue

            if _should_ignore(entry, ignore_patterns):
                # 如果该文件名符合 ignore_patterns 忽略模式，则跳过
                continue

            stat = entry.stat()  # 获取文件的统计信息
            # 生成一个 SearchResult 对象，并返回
            yield SearchResult(
                path=entry.resolve(),  # 获取文件的绝对路径
                size=stat.st_size,  # 获取文件的大小
                mtime=stat.st_mtime,  # 获取文件的最后修改时间
            )


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
