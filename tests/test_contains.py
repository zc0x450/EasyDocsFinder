from pathlib import Path

from easydocsfinder.search import iter_search_results


def test_contains_filters_files(tmp_path: Path) -> None:
    (tmp_path / "hit.txt").write_text("hello NEEDLE world", encoding="utf-8")
    (tmp_path / "miss.txt").write_text("hello world", encoding="utf-8")

    results = list(
        iter_search_results(
            roots=[tmp_path],
            pattern="*.txt",
            ignore_patterns=[],
            max_results=None,
            contains="NEEDLE",
            encoding="utf-8",
        )
    )

    names = sorted(r.path.name for r in results)
    assert names == ["hit.txt"]
