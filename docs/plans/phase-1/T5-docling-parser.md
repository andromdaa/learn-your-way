# T5 - Docling PDF Parser to ParsedDocument

## Status

- [ ] T5: Docling PDF parser to `ParsedDocument`

## Goal

Wrap Docling to produce a `ParsedDocument` with page and character
offsets. `ParsedDocument` is not part of the schema-locked
`lesson_graph.models`; it belongs in `lyw_core.parser.models` so it
can evolve without `SCHEMA_CHANGE=1`.

## Files

- Create `src/lyw_core/parser/__init__.py`.
- Create `src/lyw_core/parser/models.py` with `ParsedDocument` and
  `ParsedBlock`.
- Create `src/lyw_core/parser/docling.py`.
- Create `tests/fixtures/generate_tiny_pdf.py`; do not commit a
  binary fixture.
- Create `tests/unit/test_parser.py`.
- Modify `pyproject.toml` to add `docling` to runtime deps and the
  chosen PDF generation library to `dev` extras.

## Depends On

- T1.

## Acceptance

- `uv run pytest tests/unit/test_parser.py` passes.
- `ParsedDocument.text[span.char_start:span.char_end]` returns the
  expected substring for hand-picked spans.
- `uv run mypy` is strict-clean.
- Add an initially skipped integration test at
  `tests/integration/test_parser_openstax.py` for the gitignored
  OpenStax fixture.

## Out of Scope

- Chunking.
- Figure or table extraction beyond Docling defaults.
- OCR for scanned PDFs.

## Risk Notes

- Prefer offsets anchored to a single document-level text stream.
- If using `fpdf2` for fixture generation, record the new dev
  dependency decision in the index.
