"""Unit tests for lyw_core.parser.

Mocks DocumentConverter.convert() with a programmatically-built DoclingDocument
so that unit tests run without ML model inference. Real inference is exercised
only in tests/integration/test_parser_openstax.py.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from docling.datamodel.accelerator_options import (
    AcceleratorDevice,
    AcceleratorOptions,
)
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import DoclingDocument
from docling_core.types.doc import DocItemLabel
from docling_core.types.doc.document import (
    BoundingBox,
    CoordOrigin,
    ProvenanceItem,
    Size,
)

from lyw_core.parser.docling import DoclingParser
from lyw_core.parser.models import ParsedDocument

_HEADING = "Introduction"
_BODY = "This section introduces the core concepts."
_HEADING2 = "Conclusion"
_BODY2 = "All concepts have been covered."


def _build_docling_doc() -> DoclingDocument:
    doc = DoclingDocument(name="tiny_test")
    doc.add_page(page_no=1, size=Size(width=595, height=842))
    prov = ProvenanceItem(
        page_no=1,
        bbox=BoundingBox(l=0, t=0, r=595, b=842, coord_origin=CoordOrigin.TOPLEFT),
        charspan=(0, 0),
    )
    doc.add_heading(text=_HEADING, orig=_HEADING, level=1, prov=prov)
    doc.add_text(label=DocItemLabel.TEXT, text=_BODY, orig=_BODY, prov=prov)
    doc.add_heading(text=_HEADING2, orig=_HEADING2, level=1, prov=prov)
    doc.add_text(label=DocItemLabel.TEXT, text=_BODY2, orig=_BODY2, prov=prov)
    return doc


@pytest.fixture()
def parsed(tmp_path: Path) -> ParsedDocument:
    fake_pdf = tmp_path / "tiny_test.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 placeholder")

    mock_result = MagicMock()
    mock_result.document = _build_docling_doc()

    with patch(
        "lyw_core.parser.docling.DocumentConverter.convert",
        return_value=mock_result,
    ):
        return DoclingParser().parse(fake_pdf)


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------


def test_parsed_document_has_blocks(parsed: ParsedDocument) -> None:
    assert len(parsed.blocks) > 0


def test_parsed_document_page_count(parsed: ParsedDocument) -> None:
    assert parsed.page_count >= 1


def test_parsed_document_text_nonempty(parsed: ParsedDocument) -> None:
    assert len(parsed.text) > 0


def test_source_path_recorded(parsed: ParsedDocument, tmp_path: Path) -> None:
    assert parsed.source_path.endswith("tiny_test.pdf")


# ---------------------------------------------------------------------------
# Offset invariant — the core acceptance criterion
# ---------------------------------------------------------------------------


def test_offset_invariant_all_blocks(parsed: ParsedDocument) -> None:
    for block in parsed.blocks:
        extracted = parsed.text[block.char_start : block.char_end]
        assert extracted == block.text, (
            f"block {block.block_id!r}: "
            f"text[{block.char_start}:{block.char_end}] = {extracted!r}, "
            f"expected {block.text!r}"
        )


def test_first_block_hand_picked_span(parsed: ParsedDocument) -> None:
    first = parsed.blocks[0]
    assert first.text != ""
    assert parsed.text[first.char_start : first.char_end] == first.text


def test_known_heading_span(parsed: ParsedDocument) -> None:
    heading = next(b for b in parsed.blocks if b.text == _HEADING)
    assert parsed.text[heading.char_start : heading.char_end] == _HEADING


def test_known_body_span(parsed: ParsedDocument) -> None:
    body = next(b for b in parsed.blocks if b.text == _BODY)
    assert parsed.text[body.char_start : body.char_end] == _BODY


# ---------------------------------------------------------------------------
# Block fields
# ---------------------------------------------------------------------------


def test_blocks_have_page_numbers(parsed: ParsedDocument) -> None:
    for block in parsed.blocks:
        assert block.page_number >= 1


def test_blocks_have_non_empty_ids(parsed: ParsedDocument) -> None:
    ids = [b.block_id for b in parsed.blocks]
    assert all(bid != "" for bid in ids)
    assert len(ids) == len(set(ids)), "block_ids must be unique"


def test_blocks_have_block_type(parsed: ParsedDocument) -> None:
    for block in parsed.blocks:
        assert block.block_type != ""


# ---------------------------------------------------------------------------
# Offset ordering and coverage
# ---------------------------------------------------------------------------


def test_block_offsets_are_non_negative(parsed: ParsedDocument) -> None:
    for block in parsed.blocks:
        assert block.char_start >= 0
        assert block.char_end >= block.char_start


def test_block_offsets_within_text_bounds(parsed: ParsedDocument) -> None:
    n = len(parsed.text)
    for block in parsed.blocks:
        assert block.char_end <= n, (
            f"block {block.block_id!r} char_end {block.char_end} > text length {n}"
        )


# ---------------------------------------------------------------------------
# Accelerator wiring
# ---------------------------------------------------------------------------


def test_accelerator_options_propagate_to_pdf_pipeline() -> None:
    with patch("lyw_core.parser.docling.DocumentConverter") as mock_dc:
        DoclingParser(AcceleratorOptions(device=AcceleratorDevice.CUDA))

    fmt_options = mock_dc.call_args.kwargs["format_options"]
    pdf_opt = fmt_options[InputFormat.PDF]
    assert pdf_opt.pipeline_options.accelerator_options.device == "cuda"
