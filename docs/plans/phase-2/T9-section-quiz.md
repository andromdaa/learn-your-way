# T9 — Section Quiz Generator + Glows/Grows Feedback (Snapshot Tests)

## Status

- [ ] T9: Section quiz generator + Glows/Grows

## Goal

Build `SectionQuizGenerator` in `lyw_core/assessment/quiz.py`. Takes a
list of `ConceptNode` instances (one section) and produces 5–10
`AssessmentItem`s by calling the `MCQGenerator` per concept. Persists
items via the DAO from T8.

Adds `generate_glows_grows(items, attempts)` which produces a
`GlowsGrows(glows: str, grows: str)` summary after quiz completion,
using the `ModelClient`. `GlowsGrows` is a frozen dataclass in
`lyw_core/assessment/quiz.py`; it is intentionally not subject to the
source faithfulness validator because it is meta-commentary on learner
performance, not an educational claim about the subject matter.

Unit tests mock both the `MCQGenerator` and the `ModelClient`. Real
Ollama calls in `tests/integration/` behind `@pytest.mark.integration`.

## Files

- Create `src/lyw_core/assessment/quiz.py`.
- Create `src/lyw_core/assessment/prompts/quiz.py`.
- Create `tests/unit/test_quiz.py`.

## Depends On

- T8 (`MCQGenerator` and item DAO).

## Acceptance

- `SectionQuizGenerator(mcq_generator: MCQGenerator,
  model_client: ModelClient, dao: LywDao)` class.
- `.generate(concepts: list[ConceptNode], lesson_graph: LessonGraph) ->
  list[AssessmentItem]`; returns 1–10 items; items are persisted via
  `dao.add_assessment_item`.
- `.generate_glows_grows(items: list[AssessmentItem],
  attempts: list[dict[str, Any]]) -> GlowsGrows`.
- `GlowsGrows` frozen dataclass: `glows: str`, `grows: str`.
- Unit test: mocked `MCQGenerator` returns 2 items per concept for a
  3-concept section → 6 items total; syrupy snapshot asserts item list
  shape. Mocked `ModelClient` returns fixed Glows/Grows text; snapshot
  asserts `GlowsGrows` fields.
- `ruff check`, `mypy`, `pytest` all pass.

## Out of Scope

- Coverage, emphasis, active learning validators (T10 wires these in
  after T9).
- `AttemptRecord` full model (T12 defines it; T9 uses `dict[str, Any]`
  as a stub and can be tightened after T12 ships).
- Glows/Grows in the API response (T13).

## Risk Notes

- "5–10 items per section": if a section has only 1 concept and the
  MCQ generator yields 1 item, return that 1 item. The coverage
  validator (T10) flags insufficient coverage independently.
- `list[dict[str, Any]]` for attempts is intentionally loose until T12
  defines `AttemptRecord`; add a `# TODO(T12): tighten to
  list[AttemptRecord]` comment so it is not forgotten.
