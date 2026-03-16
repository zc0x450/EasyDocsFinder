from pathlib import Path

from easydocsfinder.search import iter_search_results, search


def test_iter_search_results_basic(tmp_path: Path) -> None:
    """
    测试对于单个根目录，按 pattern 过滤，不忽略任何文件的情况
    """
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "b.py").write_text("print('hi')")
    (tmp_path / "c.py").write_text("print('hey')")

    results = list(
        iter_search_results(
            roots=[tmp_path],
            pattern="*.py",
            ignore_patterns=[],
        )
    )

    found_names = sorted(p.path.name for p in results)
    assert found_names == ["b.py", "c.py"]


def test_iter_search_results_ignore(tmp_path: Path) -> None:
    """
    测试对于单个根目录，按 pattern 过滤，忽略指定文件的情况
    """
    (tmp_path / "a.py").write_text("a")
    (tmp_path / "b.py").write_text("b")

    results = list(
        iter_search_results(
            roots=[tmp_path],
            pattern="*.py",
            ignore_patterns=["b.py"],
        )
    )

    found_names = sorted(p.path.name for p in results)
    assert found_names == ["a.py"]


def test_search_multiple_roots(tmp_path: Path) -> None:
    """
    测试对于多个根目录，按 pattern 过滤，不忽略任何文件的情况
    """
    root1 = tmp_path / "root1"
    root2 = tmp_path / "root2"
    root1.mkdir()
    root2.mkdir()

    (root1 / "a.py").write_text("a")
    (root2 / "b.py").write_text("b")

    results = search(
        roots=[root1, root2],
        pattern="*.py",
        ignore_patterns=[],
    )

    found_names = sorted(p.path.name for p in results)
    assert found_names == ["a.py", "b.py"]
