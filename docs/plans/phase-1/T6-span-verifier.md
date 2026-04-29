# T6 - Round-Trip Span Verifier

## Status

- [ ] T6: Round-trip span verifier

## Goal

Build a pure function that receives a `ParsedDocument` and a list of
`SourceSpan`s, then returns a list of `SpanVerificationFailure`
objects. This is the truth gate for the spec requirement that 100% of
`source_spans` resolve.

## Files

- Create `src/lyw_core/parser/verifier.py`.
- Create `tests/unit/test_span_verifier.py`.
- Cover off-by-one spans, inverted spans, and empty text.
- Add hypothesis property tests: any valid span over a known document
  verifies, and any out-of-bounds span fails.
- Modify `pyproject.toml` to add `hypothesis` to `dev`.

## Depends On

- T5.

## Acceptance

- `uv run pytest tests/unit/test_span_verifier.py` passes.
- Hypothesis completes without counterexamples.
- The failure type carries the span and a document excerpt for
  diagnosis.

## Out of Scope

- Integration with the chunker.
- Integration with the CLI.
- Auto-repair. The verifier reports failures; it never patches them.

## Risk Notes

- None recorded.
