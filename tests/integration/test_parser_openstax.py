"""Integration test: parse the committed OpenStax chapter fixture.

Gates phase 2 per specs/phase-1-ingest.md acceptance criteria.
"""

from pathlib import Path

import pytest

from lyw_core.parser.docling import DoclingParser

_FIXTURE = Path(__file__).parent.parent / "fixtures" / "openstax_chapter.pdf"


@pytest.mark.skipif(
    not _FIXTURE.exists(),
    reason=f"missing fixture: {_FIXTURE}",
)
@pytest.mark.integration
def test_openstax_chapter_parses() -> None:
    parser = DoclingParser()
    doc = parser.parse(_FIXTURE)
    assert doc.page_count >= 1
    assert len(doc.blocks) > 0
    for block in doc.blocks:
        assert doc.text[block.char_start : block.char_end] == block.text
