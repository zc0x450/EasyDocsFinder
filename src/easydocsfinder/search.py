from __future__ import annotations  # 允许延迟解析类型注解

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterator, Sequence
from queue import Queue, Empty
from threading import Thread, Lock, Event


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


def _file_contains_text(
    path: Path,
    needle: str,
    *,  # 这里强制要求encoding和chunk_size必须通过关键字参数传入
    encoding: str = "utf-8",
    chunk_size: int = 64 * 1024,
) -> bool:
    if needle == "":
        # 如果needle为空字符串，则认为包含空文本的文件是符合条件的
        return True

    # 处理跨chunk匹配的情况，如果needle在chunk中间，则需要保留一部分尾巴，以便下次匹配
    # 这里尾巴的长度为needle的长度减1，因为如果需要到下一个chunk中去匹配，
    # 那么毫无疑问在第一个chunk中是不可能有needle的完整匹配的，最多只能匹配到needle的前len(needle)-1个字符
    keep = max(len(needle) - 1, 0)
    tail = ""  # 尾巴字符串

    try:
        with path.open("r", encoding=encoding, errors="ignore") as f:
            while True:
                chunk = f.read(chunk_size)  # 分块从文件中读取数据
                if not chunk:
                    # 如果读取到文件末尾还没有找到needle，则认为文件不包含needle
                    return False
                data = tail + chunk  # 将尾巴字符串和当前chunk拼接起来
                if needle in data:
                    # 如果data中包含needle，则认为文件包含needle
                    return True
                # 如果data中不包含needle，则需要保留一部分尾巴，以便下次匹配
                # 这里是从倒数第keep个字符开始保留，一直到data的末尾
                tail = data[-keep:] if keep else ""
    except OSError:
        return False


def _walk_path(
    root: Path,
    pattern: str,
    ignore_patterns: Sequence[str],
    counter: list[int],
    max_results: int | None,
    contains: str | None = None,
    encoding: str = "utf-8",
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

            # 如果指定了要搜索的文本，则需要检查文件是否包含该文本
            if contains is not None and not _file_contains_text(
                entry, contains, encoding=encoding
            ):
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
    contains: str | None = None,
    encoding: str = "utf-8",
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
        yield from _walk_path(
            root_path,
            pattern,
            ignore_patterns,
            counter,
            max_results,
            contains,
            encoding,
        )


"""
注意，上一个版本的并发函数中，我们使用的是concurrent，
原因在于，之前我们的任务是针对已经生成好的文件路径列表，对其并发地执行stat()+返回数据的操作，没有新任务产生
这非常适合通过concurrent结合ThreadPoolExecutor来实现。
而这个版本中，我们是边遍历目录，边生成结果，每遍历一个目录，就会产生新的任务，任务数量事先未知，
通过队列+长时间运行的若干个worker线程来实现，通过Queue+Thread来实现比较合适。
"""


def search_concurrent(
    roots: Sequence[str | Path],
    pattern: str = "*",
    ignore_patterns: Sequence[str] | None = None,
    max_results: int | None = None,
    max_workers: int = 8,
    contains: str | None = None,
    encoding: str = "utf-8",
) -> list[SearchResult]:
    """
    多线程并发遍历目录树并收集结果（返回 list）。
    - 使用 Queue 分发“目录任务”
    - 使用 sentinel 哨兵安全退出线程
    - 使用 stop_event 在达到 max_results 时尽快停止扩展工作
    """
    if ignore_patterns is None:
        # 和串行版一致
        ignore_patterns = []

    # 待处理的目录队列，它是线程安全的，意味着多个线程可以同时添加/获取目录
    queue: Queue[Path] = Queue()
    # 结果收集列表（由锁保护）
    results: list[SearchResult] = []
    # 全局计数器（由锁保护）
    counter = [0]
    lock = Lock()
    stop_event = Event()

    # 初始化：将每个有效 root 放入队列
    for root in roots:
        root_path = Path(root)
        if root_path.exists() and root_path.is_dir():
            # 将根目录下的有效目录加入队列
            queue.put(root_path)

    def worker() -> None:
        while True:
            # 阻塞式获取目录任务，如果队列为空，则阻塞等待，直到有目录加入队列
            dir_path = queue.get()
            # 默认情况下，queue.get方法的block参数为True，意味着如果队列为空，则阻塞等待，直到有目录加入队列
            # 之前我们设置timeout参数为0.1，意味着如果队列为空，则最多等待0.1秒，
            # 如果0.1秒后队列仍为空，则抛出Empty异常，表示没有更多目录要处理，
            # 但这种方式测试下来不靠谱
            try:
                if dir_path is None:
                    # 获取到哨兵值，说明没有更多目录要处理
                    return

                if stop_event.is_set():
                    # 这里continue的目的是，让当前线程继续把队列中的目录任务处理完，而不是直接退出
                    # 直接退出会导致队列中的任务没有线程处理，进而导致队列永远无法join完成
                    continue

                for entry in dir_path.iterdir():
                    if stop_event.is_set():
                        # 在循环中再次确认停止事件是否被触发，如果已经触发，则提前退出循环
                        break

                    if entry.is_dir():
                        # 目录名命中忽略规则：剪枝，不再递归
                        if _name_matches_any(entry.name, ignore_patterns):
                            continue
                        # 否则，把目录加入队列，等后续线程处理
                        if not stop_event.is_set():
                            queue.put(entry)
                        else:
                            break
                    elif entry.is_file():
                        # 文件名匹配规则过滤
                        if not fnmatch(entry.name, pattern):
                            continue
                        # 文件名忽略规则过滤
                        if _name_matches_any(entry.name, ignore_patterns):
                            continue

                        # 如果指定了要搜索的文本，则需要检查文件是否包含该文本
                        if contains is not None and not _file_contains_text(
                            entry, contains, encoding=encoding
                        ):
                            continue

                        # 获取文件的统计信息
                        stat = entry.stat()
                        # 创建搜索结果对象
                        result = SearchResult(
                            path=entry.resolve(),
                            size=stat.st_size,
                            mtime=stat.st_mtime,
                        )

                        with lock:
                            if max_results is not None and counter[0] >= max_results:
                                # 向结果列表添加结果前，检查是否达到目标结果数，如果已经达到，则不再添加
                                stop_event.set()  # 设置停止事件，通知所有线程停止扩展工作
                                break
                            counter[0] += 1  # 每找到一个结果，计数器加1
                            results.append(result)  # 收集结果一定要加锁

                            if max_results is not None and counter[0] >= max_results:
                                stop_event.set()  # 向列表添加结果后，再次检查是否达到目标结果数，如果已经达到，则提前退出循环
                                break
            finally:
                # 无论发生什么，都通知队列任务完成
                queue.task_done()

    # 启动 worker 线程
    threads: list[Thread] = []
    for _ in range(max_workers):
        # 创建指定数量的worker线程，统一启动，并添加到列表中管理
        # 注意这里我们使用daemon=True，意味着当主线程退出时，这些线程也会自动退出
        t = Thread(target=worker, daemon=True)
        t.start()
        threads.append(t)

    # 等待所有目录任务处理完成
    queue.join()

    # 任务都完成后，投放哨兵值，通知所有线程退出
    for _ in range(max_workers):
        queue.put(None)

    # 等待所有哨兵值都被处理完成
    queue.join()

    # 等待所有线程结束，不关心任务是否完成，只确保所有线程都退出
    for t in threads:
        t.join()

    return results
