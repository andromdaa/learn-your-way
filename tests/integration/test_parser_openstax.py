"""Integration test: parse the gitignored OpenStax chapter fixture.

Requires tests/fixtures/openstax_chapter.pdf to be present locally.
"""

from pathlib import Path

import pytest

from lyw_core.parser.docling import DoclingParser

_FIXTURE = Path(__file__).parent.parent / "fixtures" / "openstax_chapter.pdf"


@pytest.mark.skip(reason="requires tests/fixtures/openstax_chapter.pdf — not in repo")
@pytest.mark.integration
def test_openstax_chapter_parses() -> None:
    parser = DoclingParser()
    doc = parser.parse(_FIXTURE)
    assert doc.page_count >= 1
    assert len(doc.blocks) > 0
    for block in doc.blocks:
        assert doc.text[block.char_start : block.char_end] == block.text
