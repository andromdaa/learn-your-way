"""Tests for HeuristicChunker with syrupy snapshot comparison."""

from syrupy.assertion import SnapshotAssertion

from lyw_core.chunker import HeuristicChunker
from lyw_core.parser.models import ParsedBlock, ParsedDocument
from lyw_core.parser.verifier import verify_spans

# Bodies are intentionally above _MIN_BODY_CHARS (120) so each section
# survives the scaffolding/thin-body merge pass and chunks to its own node.
# offsets verified against the parser's cursor += char_end + 1 convention
_TINY_DOC_BODY1 = (
    "This is the introduction body, providing scope, goals, and context "
    "for the chapter and the methods that follow it later."
)
_TINY_DOC_BODY2 = (
    "This describes the methods used in the experiment, including the "
    "setup, procedure, controls, and the data collection process."
)
_TINY_DOC = ParsedDocument(
    source_path="test.pdf",
    text=("Introduction\n" + _TINY_DOC_BODY1 + "\nMethods\n" + _TINY_DOC_BODY2),
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
            text=_TINY_DOC_BODY1,
            char_start=13,
            char_end=133,
        ),
        ParsedBlock(
            block_id="b3",
            page_number=1,
            block_type="section_header",
            text="Methods",
            char_start=134,
            char_end=141,
        ),
        ParsedBlock(
            block_id="b4",
            page_number=1,
            block_type="text",
            text=_TINY_DOC_BODY2,
            char_start=142,
            char_end=267,
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


def test_prerequisites_form_linear_chain() -> None:
    """Each concept (except the first) lists the previous concept as a prerequisite."""
    chunker = HeuristicChunker(doc_id="test-doc")
    nodes = chunker.chunk(_TINY_DOC)
    assert nodes[0].prerequisites == []
    assert nodes[1].prerequisites == [nodes[0].id]


def test_single_node_has_no_prerequisites() -> None:
    """A document that produces only one node must have prerequisites=[]."""
    doc = ParsedDocument(
        source_path="t.pdf",
        text="Only section.",
        blocks=[
            ParsedBlock(
                block_id="b1",
                page_number=1,
                block_type="section_header",
                text="Only section.",
                char_start=0,
                char_end=13,
            )
        ],
        page_count=1,
    )
    chunker = HeuristicChunker(doc_id="single-doc")
    nodes = chunker.chunk(doc)
    assert len(nodes) == 1
    assert nodes[0].prerequisites == []


def test_chunk_output_produces_multinode_mindmap() -> None:
    """Chunked nodes with prerequisites yield a multi-node mind map."""
    from lesson_graph.models import LessonGraph, PersonalizationProfile
    from lyw_core.modalities.mindmap import MindMapGenerator

    chunker = HeuristicChunker(doc_id="test-doc")
    nodes = chunker.chunk(_TINY_DOC)
    graph = LessonGraph(id="g1", source_id="test-doc", concepts=nodes)
    profile = PersonalizationProfile(grade_level="8", interests=["science"])
    out = MindMapGenerator().generate(graph, profile)
    # Both concepts must appear as nodes in the diagram.
    assert out.count('["') == 2


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


# ----------------------------------------------------------------------
# Helpers for scaffolding-merge tests (issue #76).
# ----------------------------------------------------------------------


def _build_doc(doc_id: str, sections: list[tuple[str, str]]) -> ParsedDocument:
    """Build a ParsedDocument from a list of (heading, body) string pairs.

    Block offsets follow the parser convention (cursor += char_end + 1) so
    spans round-trip cleanly through ``verify_spans``. An empty body string
    means the section has only a heading block.
    """
    blocks: list[ParsedBlock] = []
    parts: list[str] = []
    cursor = 0
    block_index = 0
    for heading, body in sections:
        blocks.append(
            ParsedBlock(
                block_id=f"b{block_index}",
                page_number=1,
                block_type="section_header",
                text=heading,
                char_start=cursor,
                char_end=cursor + len(heading),
            )
        )
        parts.append(heading)
        cursor += len(heading) + 1  # newline separator
        block_index += 1
        if body:
            blocks.append(
                ParsedBlock(
                    block_id=f"b{block_index}",
                    page_number=1,
                    block_type="text",
                    text=body,
                    char_start=cursor,
                    char_end=cursor + len(body),
                )
            )
            parts.append(body)
            cursor += len(body) + 1
            block_index += 1
    text = "\n".join(parts)
    return ParsedDocument(
        source_path=f"{doc_id}.pdf",
        text=text,
        blocks=blocks,
        page_count=1,
    )


_REAL_BODY_LONG = (
    "A linear equation in one variable can be written in the standard form "
    "ax + b = 0, where a and b are real constants and a is non-zero."
)  # 134 chars — above _MIN_BODY_CHARS (120)


def test_solution_heading_merged_into_parent_section() -> None:
    """A 'Solution' subheading folds into the preceding pedagogical section."""
    doc = _build_doc(
        "merge-solution",
        [
            ("Linear Equations", _REAL_BODY_LONG),
            (
                "Solution",
                "Subtract b from both sides, then divide by a to isolate x.",
            ),
        ],
    )
    chunker = HeuristicChunker(doc_id="merge-solution")
    nodes = chunker.chunk(doc)
    assert len(nodes) == 1
    assert nodes[0].title == "Linear Equations"
    assert "Solution" in nodes[0].summary
    assert "Subtract b from both sides" in nodes[0].summary
    failures = verify_spans(doc, [s for n in nodes for s in n.source_spans])
    assert failures == [], failures


def test_example_n_heading_merged_into_parent() -> None:
    """An 'EXAMPLE 1' subheading folds into its parent concept."""
    doc = _build_doc(
        "merge-example",
        [
            ("Quadratic Functions", _REAL_BODY_LONG),
            (
                "EXAMPLE 1",
                "Solve x squared minus four equals zero by factoring the difference of squares.",
            ),
        ],
    )
    nodes = HeuristicChunker(doc_id="merge-example").chunk(doc)
    assert len(nodes) == 1
    assert nodes[0].title == "Quadratic Functions"
    assert "EXAMPLE 1" in nodes[0].summary


def test_learning_objectives_merged_into_parent() -> None:
    """A 'Learning Objectives' subheading folds into the parent concept."""
    doc = _build_doc(
        "merge-lo",
        [
            ("Linear Equations", _REAL_BODY_LONG),
            (
                "Learning Objectives",
                "Solve linear equations and graph their solutions on the number line.",
            ),
        ],
    )
    nodes = HeuristicChunker(doc_id="merge-lo").chunk(doc)
    assert len(nodes) == 1
    assert nodes[0].title == "Linear Equations"


def test_short_body_section_merged_into_parent() -> None:
    """A non-scaffolding heading with a < _MIN_BODY_CHARS body merges up."""
    doc = _build_doc(
        "merge-thin",
        [
            ("Linear Equations", _REAL_BODY_LONG),
            ("Recap", "Short note."),  # 11-char body, well under threshold
        ],
    )
    nodes = HeuristicChunker(doc_id="merge-thin").chunk(doc)
    assert len(nodes) == 1
    assert nodes[0].title == "Linear Equations"
    assert "Recap" in nodes[0].summary
    assert "Short note." in nodes[0].summary


def test_short_body_one_paragraph_definition_survives() -> None:
    """A body of ~135 chars under a legitimate heading remains standalone.

    Regression guard against over-aggressive thresholding: one-paragraph
    definitions are valid pedagogical units and must survive the merge.
    """
    paragraph = (
        "An inequality compares two expressions using a relational operator "
        "such as less-than, greater-than, or one of their inclusive variants."
    )
    assert len(paragraph) >= 120
    doc = _build_doc(
        "keep-paragraph",
        [
            ("Linear Equations", _REAL_BODY_LONG),
            ("Inequalities", paragraph),
        ],
    )
    nodes = HeuristicChunker(doc_id="keep-paragraph").chunk(doc)
    assert len(nodes) == 2
    assert [n.title for n in nodes] == ["Linear Equations", "Inequalities"]


def test_first_section_scaffolding_kept_as_root() -> None:
    """If the very first heading is scaffolding, retain it (no parent to merge into)."""
    doc = _build_doc(
        "first-scaffolding",
        [
            ("Solution", "Subtract b from both sides, then divide by a."),
            ("Linear Equations", _REAL_BODY_LONG),
        ],
    )
    nodes = HeuristicChunker(doc_id="first-scaffolding").chunk(doc)
    # First section is always retained even if scaffolding-shaped.
    assert len(nodes) == 2
    assert nodes[0].title == "Solution"
    assert nodes[1].title == "Linear Equations"


def test_chapter_like_input_yields_pedagogical_concepts() -> None:
    """A chapter-shaped fixture with scaffolding subheadings yields few concepts.

    Mimics one OpenStax chapter section: a real heading followed by a
    burst of Solution / Analysis / EXAMPLE N / Learning Objectives /
    MEDIA / TRY IT subheadings. All scaffolding folds back into the
    parent; the chapter shrinks to a small number of pedagogical nodes
    rather than the 8+ produced by the unfiltered splitter.
    """
    sections = [
        ("Linear Equations", _REAL_BODY_LONG),
        ("Learning Objectives", "Solve linear equations in one variable."),
        ("EXAMPLE 1", "Solve 3x + 2 = 11 step by step."),
        ("Solution", "Subtract 2 from both sides; divide by 3; x = 3."),
        ("Analysis", "Verify by substituting x = 3 back into the equation."),
        ("TRY IT #1", "Solve 5x - 7 = 18 on your own."),
        ("MEDIA", "Watch the linked video for a worked walkthrough."),
        (
            "Real-World Applications",
            "Linear models appear in budgeting, distance-time problems, and unit conversions across science.",
        ),
        ("Quadratic Functions", _REAL_BODY_LONG),
        ("EXAMPLE 1", "Factor x squared minus nine over the reals."),
        ("Solution", "Recognize a difference of squares; factor as (x-3)(x+3)."),
    ]
    doc = _build_doc("chapter-shape", sections)
    nodes = HeuristicChunker(doc_id="chapter-shape").chunk(doc)
    titles = [n.title for n in nodes]
    assert titles == ["Linear Equations", "Quadratic Functions"], titles
    # Each surviving concept's summary must include the merged-in scaffolding text.
    assert "EXAMPLE 1" in nodes[0].summary
    assert "Solution" in nodes[0].summary
    failures = verify_spans(doc, [s for n in nodes for s in n.source_spans])
    assert failures == [], failures
