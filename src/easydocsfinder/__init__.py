import sys


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    print("EasyDocsFinder CLI running...")
    print(f"Arguments: {argv}")


if __name__ == "__main__":
    main()
