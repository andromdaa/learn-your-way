# T0c-r1 — PersonalizationProfile + ReplacementRecord Schema Change (ADR-0009)

## Status

- [ ] T0c-r1: PersonalizationProfile schema change

## Goal

Replace `DerivedAsset.personalization_profile: dict[str, Any]` (the
phase-1 TODO) with a typed `PersonalizationProfile` Pydantic model.
Add `ReplacementRecord` to capture the original `SourceSpan`,
replacement text, and justification string for each change made by a
personalization generator. Update `docs/02-data-model.md`. Write
ADR-0009 explaining why a Pydantic model rather than the `TypedDict`
mentioned in the original data-model doc.

This is a load-bearing prerequisite: every personalization generator
in phase 2 (T5, T7) constructs a `PersonalizationProfile` and must
find the typed model already in place.

## Files

- Modify `src/lesson_graph/models.py` — add `ReplacementRecord` and
  `PersonalizationProfile`; replace `dict[str, Any]` in `DerivedAsset`
  (**SCHEMA_CHANGE=1 required**).
- Modify `tests/unit/test_lesson_graph.py` — add invariant tests for
  the new types.
- Create `docs/adr/0009-personalization-profile-schema.md`.
- Modify `docs/02-data-model.md` — remove the `TODO(phase-2)` note and
  document the new types.

## Depends On

- None. Can run in parallel with T0c-r2 and T1.

## Acceptance

- `PersonalizationProfile` is a Pydantic model with at least:
  `grade_level: str`, `interests: list[str]`,
  `replacements: list[ReplacementRecord]`.
- `ReplacementRecord` has `original_span: SourceSpan`,
  `replacement_text: str`, `justification: str`; a field validator
  rejects empty `justification`.
- `DerivedAsset.personalization_profile` field type is
  `PersonalizationProfile` (not `dict[str, Any]`); the `# TODO` comment
  is removed.
- `test_lesson_graph.py` covers: `ReplacementRecord` with empty
  `justification` raises `ValidationError`; round-trip serialization of
  `PersonalizationProfile`; `DerivedAsset` construction with the new
  type passes.
- `ruff check`, `mypy`, `pytest` all pass.
- ADR-0009 is committed.

## Out of Scope

- `LearnerProfile` (T1).
- Any generator that uses `PersonalizationProfile` (T5, T7).
- Changes to the SQLite schema or DAO.

## Risk Notes

- `docs/02-data-model.md` says "replace with a `TypedDict`"; the spec
  says "Pydantic model (not a plain TypedDict)." ADR-0009 must record
  this discrepancy and explain the choice (validators enforce
  `ReplacementRecord` invariants; `TypedDict` cannot).
- `DerivedAsset` is used by tests in `test_lesson_graph.py`; the
  `personalization_profile={}` call sites there will need updating to
  pass a valid `PersonalizationProfile` instance.
