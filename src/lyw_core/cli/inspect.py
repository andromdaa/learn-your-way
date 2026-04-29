import sys
from pathlib import Path

from lyw_core.chunker.heuristic import HeuristicChunker
from lyw_core.cli.render import render_concept_tree
from lyw_core.parser.docling import DoclingParser


def run_inspect(pdf_path: Path) -> int:
    if not pdf_path.exists():
        print(f"error: file not found: {pdf_path}", file=sys.stderr)
        return 1

    parser = DoclingParser()
    try:
        doc = parser.parse(pdf_path)
    except Exception as exc:
        print(f"error: failed to parse {pdf_path}: {exc}", file=sys.stderr)
        return 1

    chunker = HeuristicChunker(doc_id=str(pdf_path))
    nodes = chunker.chunk(doc)
    print(render_concept_tree(nodes), end="")
    return 0
