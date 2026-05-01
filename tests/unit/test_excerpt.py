"""Unit tests for lyw_core.parser.excerpt.extract_excerpt."""

from __future__ import annotations

from lyw_core.parser.excerpt import Excerpt, extract_excerpt
from lyw_core.parser.models import ParsedDocument


def _doc(text: str) -> ParsedDocument:
    return ParsedDocument(
        source_path="/tmp/doc.pdf", text=text, blocks=[], page_count=1
    )


# ---------------------------------------------------------------------------
# Basic window extraction
# ---------------------------------------------------------------------------


def test_extract_excerpt_basic() -> None:
    doc = _doc("A" * 50 + "MATCH" + "B" * 50)
    result = extract_excerpt(doc, 50, 55, radius=10)
    assert isinstance(result, Excerpt)
    assert "MATCH" in result.text
    assert result.window_start == 40  # 50 - 10


def test_extract_excerpt_window_start_clamped_at_zero() -> None:
    doc = _doc("Hello world, this is text.")
    result = extract_excerpt(doc, 0, 5, radius=200)
    assert result.window_start == 0
    assert result.text == doc.text  # whole doc fits in window


def test_extract_excerpt_window_end_clamped_at_doc_length() -> None:
    text = "A" * 100
    doc = _doc(text)
    result = extract_excerpt(doc, 90, 100, radius=200)
    assert result.window_start == 0
    assert result.text == text


def test_extract_excerpt_custom_radius() -> None:
    doc = _doc("X" * 500)
    result = extract_excerpt(doc, 250, 260, radius=50)
    assert result.window_start == 200  # 250 - 50
    assert len(result.text) == 110  # (260 + 50) - (250 - 50) = 310 - 200 = 110


def test_extract_excerpt_empty_doc() -> None:
    doc = _doc("")
    result = extract_excerpt(doc, 0, 0, radius=100)
    assert result.text == ""
    assert result.window_start == 0


def test_extract_excerpt_span_at_start() -> None:
    doc = _doc("MATCH" + "Z" * 200)
    result = extract_excerpt(doc, 0, 5, radius=10)
    assert result.window_start == 0
    assert result.text.startswith("MATCH")


def test_extract_excerpt_span_at_end() -> None:
    doc = _doc("Z" * 200 + "MATCH")
    n = len(doc.text)
    result = extract_excerpt(doc, n - 5, n, radius=10)
    assert result.text.endswith("MATCH")
    assert result.window_start == n - 15  # (n-5) - 10


def test_window_start_allows_client_to_find_match_offset() -> None:
    text = "pre " + "MATCH" + " post"
    doc = _doc(text)
    char_start = 4
    char_end = 9
    result = extract_excerpt(doc, char_start, char_end, radius=2)
    # in-window offset
    match_in_window = result.text[
        char_start - result.window_start : char_end - result.window_start
    ]
    assert match_in_window == "MATCH"
