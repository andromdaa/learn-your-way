# T0c-r2 — AssessmentItem.concept_id Schema Change (ADR-0010)

## Status

- [ ] T0c-r2: AssessmentItem.concept_id schema change

## Goal

Add `concept_id: str` to `AssessmentItem` so the gap detector can map
a failed quiz item directly to its parent concept without a join or
secondary lookup. The field is enforced non-empty. Write ADR-0010.

This is the load-bearing prerequisite for the clarity validator (T4),
the MCQ generator (T8), and the gap detector (T12).

## Files

- Modify `src/lesson_graph/models.py` — add `concept_id: str` to
  `AssessmentItem` (**SCHEMA_CHANGE=1 required**).
- Modify `tests/unit/test_lesson_graph.py` — add tests for the new
  field.
- Create `docs/adr/0010-assessment-item-concept-id.md`.

## Depends On

- None. Can run in parallel with T0c-r1 and T1.

## Acceptance

- `AssessmentItem.concept_id: str` field is present and enforced
  non-empty by a `@field_validator`.
- `test_lesson_graph.py`: empty `concept_id` raises `ValidationError`;
  existing `AssessmentItem` construction tests updated to supply a
  non-empty `concept_id` and still pass.
- `ruff check`, `mypy`, `pytest` all pass.
- ADR-0010 is committed.

## Out of Scope

- Runtime validation that `concept_id` resolves to a `ConceptNode` in
  a specific lesson graph (that is the clarity validator's job in T4).
- Changes to the SQLite schema (no `assessment_items` table yet; T8
  adds it).

## Risk Notes

- Existing `AssessmentItem` construction sites in the test suite
  (check `test_lesson_graph.py` before starting) must be updated to
  pass `concept_id`; doing this silently without reading the file
  first will break the PR.
