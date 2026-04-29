"""Unit tests for lyw_core.parser.verifier.

Covers:
  - off-by-one spans (char_end == len(text) + 1)
  - out-of-bounds start/end
  - empty spans (char_start == char_end)
  - inverted spans (via model_construct to bypass Pydantic)
  - happy-path single and multi-span batches
  - hypothesis properties: valid spans always pass, OOB spans always fail
"""

from hypothesis import assume, given
from hypothesis import strategies as st

from lesson_graph.models import SourceSpan
from lyw_core.parser.models import ParsedDocument
from lyw_core.parser.verifier import SpanVerificationFailure, verify_spans

_DOC_TEXT = "Hello World This Is A Test Document"
_DOC_TEXT_LEN = len(_DOC_TEXT)


def _doc(text: str = _DOC_TEXT) -> ParsedDocument:
    return ParsedDocument(source_path="test.pdf", text=text, blocks=[], page_count=1)


def _span(start: int, end: int) -> SourceSpan:
    return SourceSpan(
        doc_id="test",
        page_start=1,
        page_end=1,
        char_start=start,
        char_end=end,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_valid_span_no_failures() -> None:
    doc = _doc()
    span = _span(0, 5)
    assert verify_spans(doc, [span]) == []


def test_valid_full_span_no_failures() -> None:
    doc = _doc()
    span = _span(0, _DOC_TEXT_LEN)
    assert verify_spans(doc, [span]) == []


def test_valid_mid_span_no_failures() -> None:
    doc = _doc()
    span = _span(6, 11)  # "World"
    assert verify_spans(doc, [span]) == []


def test_empty_input_returns_no_failures() -> None:
    assert verify_spans(_doc(), []) == []


def test_multiple_valid_spans_no_failures() -> None:
    doc = _doc()
    spans = [_span(0, 5), _span(6, 11), _span(12, 16)]
    assert verify_spans(doc, spans) == []


# ---------------------------------------------------------------------------
# Off-by-one
# ---------------------------------------------------------------------------


def test_off_by_one_end_fails() -> None:
    doc = _doc()
    span = _span(0, _DOC_TEXT_LEN + 1)
    failures = verify_spans(doc, [span])
    assert len(failures) == 1


def test_off_by_one_failure_carries_span() -> None:
    doc = _doc()
    span = _span(0, _DOC_TEXT_LEN + 1)
    failure = verify_spans(doc, [span])[0]
    assert failure.span is span


def test_off_by_one_failure_carries_excerpt() -> None:
    doc = _doc()
    span = _span(0, _DOC_TEXT_LEN + 1)
    failure: SpanVerificationFailure = verify_spans(doc, [span])[0]
    assert isinstance(failure.excerpt, str)


def test_off_by_one_failure_carries_reason() -> None:
    doc = _doc()
    span = _span(0, _DOC_TEXT_LEN + 1)
    failure = verify_spans(doc, [span])[0]
    assert failure.reason != ""


# ---------------------------------------------------------------------------
# Out-of-bounds start
# ---------------------------------------------------------------------------


def test_oob_start_fails() -> None:
    doc = _doc()
    span = _span(_DOC_TEXT_LEN + 5, _DOC_TEXT_LEN + 10)
    failures = verify_spans(doc, [span])
    assert len(failures) == 1


def test_oob_start_failure_carries_span() -> None:
    doc = _doc()
    span = _span(_DOC_TEXT_LEN + 5, _DOC_TEXT_LEN + 10)
    assert verify_spans(doc, [span])[0].span is span


# ---------------------------------------------------------------------------
# Empty spans
# ---------------------------------------------------------------------------


def test_empty_span_at_zero_fails() -> None:
    doc = _doc()
    span = _span(0, 0)
    failures = verify_spans(doc, [span])
    assert len(failures) == 1


def test_empty_span_mid_fails() -> None:
    doc = _doc()
    span = _span(5, 5)
    failures = verify_spans(doc, [span])
    assert len(failures) == 1


def test_empty_span_failure_reason_mentions_empty() -> None:
    doc = _doc()
    failure = verify_spans(doc, [_span(5, 5)])[0]
    assert "empty" in failure.reason.lower()


# ---------------------------------------------------------------------------
# Inverted spans (bypassing Pydantic to test defensive check)
# ---------------------------------------------------------------------------


def test_inverted_span_fails() -> None:
    doc = _doc()
    inverted = SourceSpan.model_construct(
        doc_id="test",
        page_start=1,
        page_end=1,
        char_start=10,
        char_end=5,
    )
    failures = verify_spans(doc, [inverted])
    assert len(failures) == 1


def test_inverted_span_failure_reason_mentions_inverted() -> None:
    doc = _doc()
    inverted = SourceSpan.model_construct(
        doc_id="test",
        page_start=1,
        page_end=1,
        char_start=10,
        char_end=5,
    )
    failure = verify_spans(doc, [inverted])[0]
    assert "inverted" in failure.reason.lower()


# ---------------------------------------------------------------------------
# Mixed batch: only bad spans appear in failures
# ---------------------------------------------------------------------------


def test_mixed_batch_only_bad_spans_in_failures() -> None:
    doc = _doc()
    good = _span(0, 5)
    bad = _span(0, _DOC_TEXT_LEN + 1)
    failures = verify_spans(doc, [good, bad])
    assert len(failures) == 1
    assert failures[0].span is bad


def test_all_bad_batch() -> None:
    doc = _doc()
    spans = [_span(0, 0), _span(_DOC_TEXT_LEN + 1, _DOC_TEXT_LEN + 2)]
    failures = verify_spans(doc, spans)
    assert len(failures) == 2


# ---------------------------------------------------------------------------
# SpanVerificationFailure type
# ---------------------------------------------------------------------------


def test_failure_is_frozen() -> None:
    doc = _doc()
    span = _span(0, 0)
    failure = verify_spans(doc, [span])[0]
    try:
        failure.reason = "mutated"  # type: ignore[misc]
        raise AssertionError("Should not be mutable")
    except (AttributeError, TypeError):
        pass


# ---------------------------------------------------------------------------
# Hypothesis properties
# ---------------------------------------------------------------------------


@given(
    start=st.integers(min_value=0, max_value=_DOC_TEXT_LEN - 1),
    length=st.integers(min_value=1, max_value=_DOC_TEXT_LEN),
)
def test_property_valid_span_no_failures(start: int, length: int) -> None:
    assume(start + length <= _DOC_TEXT_LEN)
    doc = _doc()
    span = _span(start, start + length)
    assert verify_spans(doc, [span]) == []


@given(
    start=st.integers(min_value=0),
    end=st.integers(min_value=0),
)
def test_property_oob_span_fails(start: int, end: int) -> None:
    assume(start <= end)
    assume(end > _DOC_TEXT_LEN)
    doc = _doc()
    span = _span(start, end)
    failures = verify_spans(doc, [span])
    assert len(failures) == 1
