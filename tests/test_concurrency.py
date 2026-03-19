def test_main_uses_concurrent_when_flag_set(monkeypatch, capsys):
    """
    验证main函数是否正确调用了search_concurrent函数，并传递了正确的参数
    """
    import easydocsfinder

    called = {}

    def fake_search_concurrent(
        *, roots, pattern, ignore_patterns, max_results, max_workers, contains, encoding
    ):
        called["roots"] = roots
        called["pattern"] = pattern
        called["ignore_patterns"] = ignore_patterns
        called["max_results"] = max_results
        called["max_workers"] = max_workers
        called["contains"] = contains
        called["encoding"] = encoding
        return []  # 让 main() 走到 “No matching...” 分支，避免真正遍历

    # 注意：__init__.py 里是 `from .search import ...`，所以要 patch easydocsfinder.search_concurrent 这个名字
    monkeypatch.setattr(easydocsfinder, "search_concurrent", fake_search_concurrent)

    rc = easydocsfinder.main(
        [
            ".",
            "--concurrent",
            "--workers",
            "3",
            "--max-results",
            "10",
            "-p",
            "*.py",
            "-i",
            ".git",
            "--contains",
            "",
            "--encoding",
            "utf-8",
        ]
    )
    assert rc == 0

    assert called == {
        "roots": ["."],
        "pattern": "*.py",
        "ignore_patterns": [".git"],
        "max_results": 10,
        "max_workers": 3,
        "contains": "",
        "encoding": "utf-8",
    }

    out = capsys.readouterr()
    assert "No matching files found." in out.err
