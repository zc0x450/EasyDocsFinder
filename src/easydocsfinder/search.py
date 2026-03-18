from __future__ import annotations  # 允许延迟解析类型注解

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed


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
    counter: list[int],
    max_results: int | None,
) -> Iterator[SearchResult]:
    for entry in root.iterdir():
        # 如果达到最大结果数，则停止遍历(终止生成器)
        if max_results is not None and counter[0] >= max_results:
            return
        # 列出根目录下的所有文件和目录，不递归
        if entry.is_dir():
            # 目录名命中忽略规则：剪枝，不再递归
            if _name_matches_any(entry.name, ignore_patterns):
                continue
            # 否则递归进入子目录，通过yield from把子目录的搜索结果传递给父级
            yield from _walk_path(entry, pattern, ignore_patterns, counter, max_results)
        elif entry.is_file():
            # 先按 pattern 过滤
            if not fnmatch(entry.name, pattern):
                continue
            # 再按 ignore_patterns 过滤文件名
            if _name_matches_any(entry.name, ignore_patterns):
                continue

            stat = entry.stat()
            counter[0] += 1  # 每找到一个结果，计数器加1
            yield SearchResult(
                path=entry.resolve(),
                size=stat.st_size,
                mtime=stat.st_mtime,
            )


def iter_search_results(
    roots: Sequence[str | Path],
    pattern: str = "*",
    ignore_patterns: Sequence[str] | None = None,
    max_results: int | None = None,
) -> Iterator[SearchResult]:
    """
    串行遍历 roots 下的所有文件，按 pattern 过滤，并按 ignore_patterns 忽略。
    """
    if ignore_patterns is None:
        # 注意默认值为 None，需要显式转换为空列表
        ignore_patterns = []

    # 把计数器放在列表里，因为计数器是可变的，需要放在可变对象里才能被修改
    counter = [0]

    for root in roots:
        # 如果达到最大结果数，则停止遍历(终止生成器)
        if max_results is not None and counter[0] >= max_results:
            return

        # 遍历要搜索的根目录，首先转换为 Path 对象
        root_path = Path(root)
        # 如果该目录不存在或不是目录，则跳过
        if not root_path.exists() or not root_path.is_dir():
            continue
        # 递归遍历该目录下的所有文件和目录，通过yield from把子目录的搜索结果传递给父级
        yield from _walk_path(root_path, pattern, ignore_patterns, counter, max_results)


def iter_search_results_concurrent(
    roots: Sequence[str | Path],
    pattern: str = "*",
    ignore_patterns: Sequence[str] | None = None,
    max_results: int | None = None,
    max_workers: int | None = None,
) -> Iterator[SearchResult]:
    """
    使用线程池并发处理文件 stat 和结果构建。
    目录遍历仍然在主线程中完成，将文件路径收集到候选文件列表中。
    """
    if ignore_patterns is None:
        # 和串行版本一致
        ignore_patterns = []

    # 收集所有“候选文件路径”（已应用目录剪枝、pattern 和 ignore 过滤）, 这些文件路径将作为线程池的输入
    candidate_files: list[Path] = []

    for root in roots:
        root_path = Path(root)
        if not root_path.exists() or not root_path.is_dir():
            continue

        counter = [0]

        # 通过_walk_path函数遍历目录下的所有文件和目录，将文件路径收集到候选文件列表中
        for entry in _walk_path(
            root_path, pattern, ignore_patterns, counter, max_results=None
        ):
            candidate_files.append(entry.path)

            # 上面的counter用于在_walk_path中方式递归过深，找到max_results个结果后就停止再yield结果
            # 这里通过len(candidate_files)形成双保险的检查
            if max_results is not None and len(candidate_files) >= max_results:
                break

        if max_results is not None and len(candidate_files) >= max_results:
            # 这里两次检查，以跳出外层循环
            break

    if not candidate_files:
        return iter(())  # 如果没有查到候选文件，则返回空生成器

    def worker(path: Path) -> SearchResult:
        # worker就是并发中处理单个文件的函数，它返回一个SearchResult对象
        stat = path.stat()  # 针对磁盘I/O的操作应用并发
        return SearchResult(
            path=path,
            size=stat.st_size,
            mtime=stat.st_mtime,
        )

    def generate() -> Iterator[SearchResult]:
        # generate函数是并发版本的主函数，它使用线程池并发处理文件 stat 和结果构建
        count = 0
        # 创建线程池，并提交任务
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 构建一个字典，将Future对象与文件路径关联起来
            future_to_path = {executor.submit(worker, p): p for p in candidate_files}
            # as_completed函数返回一个迭代器，其中包含所有已完成任务的Future对象
            for future in as_completed(future_to_path):
                result = future.result()  # 获取任务的返回结果
                yield result  # 将结果yield出去
                count += 1
                # 如果达到最大结果数，则停止遍历(终止生成器)
                if max_results is not None and count >= max_results:
                    break

    return generate()
