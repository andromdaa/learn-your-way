"""Unit tests for SlideValidator."""

from __future__ import annotations

from lesson_graph.models import SourceSpan
from lyw_core.modalities.slides import Slide
from lyw_core.validators.slides import SlideValidator


def _span() -> SourceSpan:
    return SourceSpan(
        doc_id="doc-1", page_start=1, page_end=2, char_start=0, char_end=100
    )


def _valid_slide() -> Slide:
    return Slide(
        title="Valid Title",
        body="Valid body content.",
        speaker_notes="Speaker notes here.",
        source_spans=[_span()],
        concept_id="c1",
    )


def test_valid_slide_passes() -> None:
    result = SlideValidator().validate(_valid_slide())
    assert result.passed is True
    assert result.reason is None


def test_empty_title_fails() -> None:
    slide = Slide(
        title="",
        body="Valid body.",
        speaker_notes="Notes.",
        source_spans=[_span()],
        concept_id="c1",
    )
    result = SlideValidator().validate(slide)
    assert result.passed is False
    assert result.reason is not None
    assert "title" in result.reason.lower()


def test_empty_body_fails() -> None:
    slide = Slide(
        title="Title",
        body="",
        speaker_notes="Notes.",
        source_spans=[_span()],
        concept_id="c1",
    )
    result = SlideValidator().validate(slide)
    assert result.passed is False
    assert result.reason is not None
    assert "body" in result.reason.lower()


def test_empty_source_spans_fails() -> None:
    slide = Slide(
        title="Title",
        body="Body content.",
        speaker_notes="Notes.",
        source_spans=[],
        concept_id="c1",
    )
    result = SlideValidator().validate(slide)
    assert result.passed is False
    assert result.reason is not None
    assert "source" in result.reason.lower() or "span" in result.reason.lower()


def test_empty_concept_id_fails() -> None:
    slide = Slide(
        title="Title",
        body="Body content.",
        speaker_notes="Notes.",
        source_spans=[_span()],
        concept_id="",
    )
    result = SlideValidator().validate(slide)
    assert result.passed is False
    assert result.reason is not None
    assert "concept" in result.reason.lower()


def test_whitespace_title_fails() -> None:
    slide = Slide(
        title="   ",
        body="Valid body.",
        speaker_notes="Notes.",
        source_spans=[_span()],
        concept_id="c1",
    )
    result = SlideValidator().validate(slide)
    assert result.passed is False


def test_whitespace_body_fails() -> None:
    slide = Slide(
        title="Title",
        body="   ",
        speaker_notes="Notes.",
        source_spans=[_span()],
        concept_id="c1",
    )
    result = SlideValidator().validate(slide)
    assert result.passed is False


def test_multiple_source_spans_passes() -> None:
    slide = Slide(
        title="Title",
        body="Body.",
        speaker_notes="Notes.",
        source_spans=[_span(), _span()],
        concept_id="c1",
    )
    result = SlideValidator().validate(slide)
    assert result.passed is True
