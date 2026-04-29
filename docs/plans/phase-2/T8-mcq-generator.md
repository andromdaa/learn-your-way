# T8 — Embedded MCQ Generator + assessment_items SQLite Table + Item DAO

## Status

- [ ] T8: MCQ generator + assessment_items persistence

## Goal

Build `MCQGenerator` in `lyw_core/assessment/mcq.py`. Takes a
`ConceptNode` and generates 1–3 embedded multiple-choice questions
(4 distractors each). Each item must have `concept_id` set, at least
one `SourceSpan` that is a strict subset of the concept's span range,
a non-empty `rationale`, `correct_answer` set to the correct option
text, and `bloom_level` set to the appropriate Bloom's level. Source
faithfulness and clarity validators gate every item; items that fail
are discarded.

Add an `assessment_items` table to the SQLite schema and
`add_assessment_item` / `get_items_by_concept` to the DAO.

Unit tests mock the `ModelClient` and use an in-memory SQLite DB for
DAO tests. Real Ollama calls in `tests/integration/` behind
`@pytest.mark.integration`.

## Files

- Create `src/lyw_core/assessment/__init__.py`.
- Create `src/lyw_core/assessment/mcq.py`.
- Create `src/lyw_core/assessment/prompts/mcq.py`.
- Modify `src/lyw_core/db/schema.sql` — add `assessment_items` table.
- Modify `src/lyw_core/db/dao.py` — add item DAO methods.
- Create `tests/unit/test_mcq.py`.

## Depends On

- T0c-r2 (`AssessmentItem.concept_id`).
- T0c-r3 (`AssessmentItem.correct_answer` and `bloom_level`).
- T3 (validator framework).
- T4 (source faithfulness + clarity validators).

## Acceptance

- `MCQGenerator(model_client: ModelClient,
  validators: list[Validator[ItemValidationPayload]], dao: LywDao)`.
- `.generate(concept: ConceptNode, lesson_graph: LessonGraph) ->
  list[AssessmentItem]`; returns only items passing all validators.
- MCQ generator prompt instructs the model to emit `correct_answer`
  (the correct option text verbatim) and `bloom_level` (one of the
  six Bloom's values). Items where the model omits either field are
  discarded.
- `assessment_items` table: `id TEXT PK`, `concept_id TEXT NOT NULL`,
  `kind TEXT NOT NULL`, `prompt TEXT NOT NULL`, `rationale TEXT NOT
  NULL`, `difficulty TEXT NOT NULL`, `correct_answer TEXT`,
  `bloom_level TEXT`, `source_spans TEXT NOT NULL` (JSON). FK:
  `concept_id REFERENCES concepts(id)`.
- `add_assessment_item(item: AssessmentItem) -> None`;
  `get_items_by_concept(concept_id: str) -> list[AssessmentItem]`.
- Unit test: mocked model returns 2 items, 1 failing faithfulness;
  snapshot asserts 1 item returned; DAO round-trip tested with
  in-memory SQLite.
- `ruff check`, `mypy`, `pytest` all pass.

## Out of Scope

- Section-level quiz assembly (T9).
- Mnemonic generation (T11).

## Risk Notes

- Reuse the `span_is_contained(item_span, concept_spans)` helper
  defined in T4 rather than re-implementing the span-subset check.
- `assessment_items.concept_id` references `concepts.id` which is
  populated by the ingest pipeline. For unit tests that skip full
  ingest, set `PRAGMA foreign_keys = OFF` or pre-insert the concept
  row in the fixture.
