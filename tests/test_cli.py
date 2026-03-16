from easydocsfinder import parse_args


def test_parse_args_basic():
    args = parse_args([".", "-p", "*.py", "-i", ".git", "-i", "*.log"])

    assert args.roots == ["."]
    assert args.pattern == "*.py"
    assert args.ignore == [".git", "*.log"]
