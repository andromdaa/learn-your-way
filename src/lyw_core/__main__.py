import argparse
import sys
from pathlib import Path

from lyw_core.cli.inspect import run_inspect


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m lyw_core",
        description="Learn Your Way — source inspection tool",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ins = sub.add_parser("inspect", help="parse a PDF and print the concept tree")
    ins.add_argument("pdf_path", type=Path, help="path to the PDF file to inspect")

    args = parser.parse_args()
    if args.command == "inspect":
        sys.exit(run_inspect(args.pdf_path))


if __name__ == "__main__":
    main()
