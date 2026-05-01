"""Tests for the inspection CLI (python -m lyw_core inspect)."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from lesson_graph.models import ConceptNode, SourceSpan
from lyw_core.cli.inspect import run_inspect
from lyw_core.cli.render import render_concept_tree
from lyw_core.parser.models import ParsedBlock, ParsedDocument

_FIXTURE_PDF = Path(__file__).parent.parent / "fixtures" / "tiny_test.pdf"

# Bodies are intentionally above the chunker's _MIN_BODY_CHARS (120)
# threshold so each section produces its own concept node.
_PARSED_BODY1 = (
    "This is the introduction body, providing scope, goals, and context "
    "for the chapter and the methods that follow it later."
)
_PARSED_BODY2 = (
    "This describes the methods used in the experiment, including the "
    "setup, procedure, controls, and the data collection process."
)
_PARSED_DOC = ParsedDocument(
    source_path="test.pdf",
    text=("Introduction\n" + _PARSED_BODY1 + "\nMethods\n" + _PARSED_BODY2),
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
            text=_PARSED_BODY1,
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
            text=_PARSED_BODY2,
            char_start=142,
            char_end=267,
        ),
    ],
    page_count=1,
)

_NODES = [
    ConceptNode(
        id="01e6b44ba385",
        title="Introduction",
        summary="This is the body.",
        learning_objective="Understand Introduction",
        source_spans=[
            SourceSpan(
                doc_id="test.pdf", page_start=1, page_end=1, char_start=0, char_end=30
            )
        ],
        prerequisites=[],
        provenance="heuristic",
    ),
    ConceptNode(
        id="8ba47661dbda",
        title="Methods",
        summary="More content here.",
        learning_objective="Understand Methods",
        source_spans=[
            SourceSpan(
                doc_id="test.pdf", page_start=1, page_end=1, char_start=31, char_end=57
            )
        ],
        prerequisites=["01e6b44ba385"],
        provenance="heuristic",
    ),
]


# ---------------------------------------------------------------------------
# render_concept_tree — pure unit tests
# ---------------------------------------------------------------------------


def test_render_tree_snapshot(snapshot: SnapshotAssertion) -> None:
    result = render_concept_tree(_NODES)
    assert snapshot == result


def test_render_tree_contains_all_titles() -> None:
    result = render_concept_tree(_NODES)
    assert "Introduction" in result
    assert "Methods" in result


def test_render_tree_contains_objectives() -> None:
    result = render_concept_tree(_NODES)
    assert "Understand Introduction" in result
    assert "Understand Methods" in result


def test_render_tree_contains_spans() -> None:
    result = render_concept_tree(_NODES)
    assert "0" in result
    assert "30" in result


def test_render_tree_shows_prerequisites() -> None:
    result = render_concept_tree(_NODES)
    assert "01e6b44ba385" in result


def test_render_tree_empty() -> None:
    result = render_concept_tree([])
    assert "Concepts (0)" in result


def test_render_single_node_no_prereqs() -> None:
    node = ConceptNode(
        id="abc",
        title="Solo",
        summary="A lone node.",
        learning_objective="Understand Solo",
        source_spans=[
            SourceSpan(
                doc_id="d.pdf", page_start=1, page_end=1, char_start=0, char_end=10
            )
        ],
        prerequisites=[],
        provenance="heuristic",
    )
    result = render_concept_tree([node])
    assert "(none)" in result


# ---------------------------------------------------------------------------
# run_inspect — in-process tests with mocked parser
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_parse() -> ParsedDocument:
    return _PARSED_DOC


def test_run_inspect_exit_zero(tmp_path: Path, mock_parse: ParsedDocument) -> None:
    fake_pdf = tmp_path / "fake.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4")
    with patch("lyw_core.cli.inspect.DoclingParser") as mock_cls:
        mock_cls.return_value.parse.return_value = mock_parse
        code = run_inspect(fake_pdf)
    assert code == 0


def test_run_inspect_stdout_snapshot(
    mock_parse: ParsedDocument,
    capsys: pytest.CaptureFixture[str],
    snapshot: SnapshotAssertion,
) -> None:
    # Use the stable fixture path so the chunker's doc_id-derived node IDs are deterministic.
    with patch("lyw_core.cli.inspect.DoclingParser") as mock_cls:
        mock_cls.return_value.parse.return_value = mock_parse
        run_inspect(_FIXTURE_PDF)
    captured = capsys.readouterr()
    assert snapshot == captured.out


def test_run_inspect_at_least_one_concept(
    tmp_path: Path,
    mock_parse: ParsedDocument,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_pdf = tmp_path / "fake.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4")
    with patch("lyw_core.cli.inspect.DoclingParser") as mock_cls:
        mock_cls.return_value.parse.return_value = mock_parse
        run_inspect(fake_pdf)
    out = capsys.readouterr().out
    assert "Concepts" in out
    # At least one node rendered
    assert "├──" in out or "└──" in out


def test_run_inspect_nonexistent_file_exits_nonzero() -> None:
    code = run_inspect(Path("/nonexistent/path/file.pdf"))
    assert code != 0


# ---------------------------------------------------------------------------
# subprocess entry point — integration
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_subprocess_entrypoint_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "lyw_core", "inspect", str(_FIXTURE_PDF)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Concepts" in result.stdout
