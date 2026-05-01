"""Excerpt extraction from a ParsedDocument.

Used by the API excerpt endpoint to return a character-window around a span.
"""

from __future__ import annotations

from dataclasses import dataclass

from lyw_core.parser.models import ParsedDocument


@dataclass(frozen=True)
class Excerpt:
    """A window of text extracted from a document.

    window_start is the char offset of the window's start within the full
    document text, so the highlighted slice sits at
    text[char_start - window_start : char_end - window_start].
    """

    text: str
    window_start: int


def extract_excerpt(
    doc: ParsedDocument,
    char_start: int,
    char_end: int,
    *,
    radius: int = 200,
) -> Excerpt:
    """Return a text window around [char_start, char_end) with the given radius.

    Clamps to document boundaries so the window is always valid.
    """
    n = len(doc.text)
    window_start = max(0, char_start - radius)
    window_end = min(n, char_end + radius)
    return Excerpt(text=doc.text[window_start:window_end], window_start=window_start)
