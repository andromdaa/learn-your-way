from dataclasses import dataclass

from lesson_graph.models import SourceSpan
from lyw_core.parser.models import ParsedDocument

_EXCERPT_RADIUS = 20


@dataclass(frozen=True)
class SpanVerificationFailure:
    span: SourceSpan
    excerpt: str
    reason: str


def verify_spans(
    doc: ParsedDocument,
    spans: list[SourceSpan],
) -> list[SpanVerificationFailure]:
    """Return failures for every span that does not resolve cleanly in doc.

    Checks (in order):
      1. Inverted: char_end < char_start (model_construct can bypass Pydantic).
      2. Out-of-bounds: char_start or char_end exceeds len(doc.text).
      3. Empty: char_start == char_end.
    """
    failures: list[SpanVerificationFailure] = []
    text = doc.text
    n = len(text)

    for span in spans:
        reason: str | None = None

        if span.char_end < span.char_start:
            reason = (
                f"inverted span: char_end ({span.char_end}) "
                f"< char_start ({span.char_start})"
            )
        elif span.char_start > n or span.char_end > n:
            reason = (
                f"out of bounds: span [{span.char_start}, {span.char_end}) "
                f"exceeds document length {n}"
            )
        elif span.char_start == span.char_end:
            reason = "empty span: char_start == char_end resolves to no text"

        if reason is not None:
            anchor = min(span.char_start, n)
            excerpt_start = max(0, anchor - _EXCERPT_RADIUS)
            excerpt_end = min(n, anchor + _EXCERPT_RADIUS)
            failures.append(
                SpanVerificationFailure(
                    span=span,
                    excerpt=text[excerpt_start:excerpt_end],
                    reason=reason,
                )
            )

    return failures
