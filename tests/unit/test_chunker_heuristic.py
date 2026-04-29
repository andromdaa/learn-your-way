"""Tests for HeuristicChunker with syrupy snapshot comparison."""

from syrupy.assertion import SnapshotAssertion

from lyw_core.chunker import HeuristicChunker
from lyw_core.parser.models import ParsedBlock, ParsedDocument
from lyw_core.parser.verifier import verify_spans

# "Introduction\nThis is the body.\nMethods\nMore content here."
# offsets verified against the parser's cursor += char_end + 1 convention
_TINY_DOC = ParsedDocument(
    source_path="test.pdf",
    text="Introduction\nThis is the body.\nMethods\nMore content here.",
    blocks=[
        ParsedBlock(
            block_id="b1",
            page_number=1,
            block_type="section_header",
            text="Introduction",
            char_start=0,
            char_end=12,
        ),
        ParsedBlock(
            block_id="b2",
            page_number=1,
            block_type="text",
            text="This is the body.",
            char_start=13,
            char_end=30,
        ),
        ParsedBlock(
            block_id="b3",
            page_number=1,
            block_type="section_header",
            text="Methods",
            char_start=31,
            char_end=38,
        ),
        ParsedBlock(
            block_id="b4",
            page_number=1,
            block_type="text",
            text="More content here.",
            char_start=39,
            char_end=57,
        ),
    ],
    page_count=1,
)


def test_chunks_heading_per_section(snapshot: SnapshotAssertion) -> None:
    chunker = HeuristicChunker(doc_id="test-doc")
    nodes = chunker.chunk(_TINY_DOC)
    assert len(nodes) == 2
    assert [n.title for n in nodes] == ["Introduction", "Methods"]
    assert snapshot == [n.model_dump() for n in nodes]


def test_all_nodes_have_heuristic_provenance() -> None:
    chunker = HeuristicChunker(doc_id="test-doc")
    nodes = chunker.chunk(_TINY_DOC)
    assert all(n.provenance == "heuristic" for n in nodes)


def test_span_roundtrip_passes_verifier() -> None:
    chunker = HeuristicChunker(doc_id="test-doc")
    nodes = chunker.chunk(_TINY_DOC)
    all_spans = [span for n in nodes for span in n.source_spans]
    failures = verify_spans(_TINY_DOC, all_spans)
    assert failures == [], failures


def test_single_section_no_heading() -> None:
    """A document with no heading blocks produces one node."""
    doc = ParsedDocument(
        source_path="t.pdf",
        text="Some plain text here.",
        blocks=[
            ParsedBlock(
                block_id="b1",
                page_number=1,
                block_type="text",
                text="Some plain text here.",
                char_start=0,
                char_end=21,
            )
        ],
        page_count=1,
    )
    chunker = HeuristicChunker(doc_id="plain-doc")
    nodes = chunker.chunk(doc)
    assert len(nodes) == 1
    assert nodes[0].provenance == "heuristic"
    assert nodes[0].source_spans[0].char_start == 0
    assert nodes[0].source_spans[0].char_end == 21


def test_long_body_splits_at_block_boundary() -> None:
    """Multiple body blocks exceeding max_chars are split into separate nodes."""
    body1 = "x" * 40
    body2 = "y" * 40
    # "Heading\n" + body1 + "\n" + body2 → len = 7+1+40+1+40 = 89
    doc = ParsedDocument(
        source_path="t.pdf",
        text="Heading\n" + body1 + "\n" + body2,
        blocks=[
            ParsedBlock(
                block_id="b1",
                page_number=1,
                block_type="section_header",
                text="Heading",
                char_start=0,
                char_end=7,
            ),
            ParsedBlock(
                block_id="b2",
                page_number=1,
                block_type="text",
                text=body1,
                char_start=8,
                char_end=48,
            ),
            ParsedBlock(
                block_id="b3",
                page_number=1,
                block_type="text",
                text=body2,
                char_start=49,
                char_end=89,
            ),
        ],
        page_count=1,
    )
    # heading(7) + body1(40) = 47 chars ≤ 50; adding body2 would push to 88 > 50
    chunker = HeuristicChunker(doc_id="long-doc", max_chars=50)
    nodes = chunker.chunk(doc)
    assert len(nodes) == 2
    all_spans = [s for n in nodes for s in n.source_spans]
    failures = verify_spans(doc, all_spans)
    assert failures == [], failures
