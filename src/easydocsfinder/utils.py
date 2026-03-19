from pathlib import Path


def _print_content_matches(path: Path, needle: str, encoding: str = "utf-8") -> None:
    """
    在终端打印文件中所有包含 needle 的行：行号、列号和该行内容。
    """
    try:
        with path.open("r", encoding=encoding, errors="ignore") as f:
            for lineno, line in enumerate(f, start=1):
                # 获取行号和行内容
                idx = line.find(needle)  # 查找needle在行中的位置
                if idx == -1:
                    # 如果needle不在行中，则跳过
                    continue
                # 去掉末尾换行，避免输出多余空行
                text = line.rstrip("\n\r")
                print(f"    line {lineno}, col {idx + 1}: {text}")
    except OSError:
        # 读不到就忽略，不影响整体结果
        return
