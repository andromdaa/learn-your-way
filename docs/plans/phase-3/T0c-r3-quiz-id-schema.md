# T0c-r3 — quiz_id schema change + DAO + SectionQuizGenerator wiring

## ID and one-line summary

T0c-r3: Add `quiz_id: str | None = None` to `AssessmentItem`, add `quiz_id`
columns to the `assessment_items` and `attempts` SQLite tables, update DAO
methods, and wire `SectionQuizGenerator` to populate `quiz_id` at persistence
time (`SCHEMA_CHANGE=1`, ADR-0015).

## Goal

`POST /v1/attempts` currently cannot surface Glows-Grows feedback because
there is no link between an `AttemptRecord` and its parent `SectionQuiz`.
This task adds that link by:

1. Adding `quiz_id: str | None = None` to `AssessmentItem` in
   `lesson_graph/models.py`. Default `None` preserves backward compatibility
   with existing serialised items (embedded MCQs, which are not part of a
   section quiz, stay `quiz_id=None`).
2. Adding `quiz_id TEXT` columns (nullable) to `assessment_items` and
   `attempts` in `schema.sql` (via `ALTER TABLE ... ADD COLUMN IF NOT
   EXISTS`, so a fresh schema and an existing database both work).
3. Updating `Database.add_assessment_item` and `Database.record_attempt` in
   `dao.py` to read and write the new column, and adding
   `get_items_by_quiz_id(quiz_id: str) -> list[AssessmentItem]` for T0c-r4 to
   call.
4. Updating `SectionQuizGenerator.generate` to pass a caller-supplied
   `quiz_id` (a fresh `uuid.uuid4()` generated at quiz-generation time) to
   `MCQGenerator`, which in turn passes it to `add_assessment_item`. Each item
   in the quiz carries the same `quiz_id`.

ADR-0015 documents the decision to add `quiz_id` as a nullable denormalised
field rather than a join table.

## Files created or modified

- `src/lesson_graph/models.py` — **modify** (`SCHEMA_CHANGE=1`): add
  `quiz_id: str | None = None` to `AssessmentItem`.
- `src/lyw_core/db/schema.sql` — **modify**: add nullable `quiz_id TEXT`
  column to both `assessment_items` and `attempts`.
- `src/lyw_core/db/dao.py` — **modify**: update `add_assessment_item`,
  `record_attempt`, `get_item_by_id`, and `get_items_by_concept` to
  read/write `quiz_id`; add `get_items_by_quiz_id(quiz_id: str) ->
  list[AssessmentItem]`.
- `src/lyw_core/assessment/quiz.py` — **modify**: `SectionQuizGenerator.generate`
  now accepts an optional `quiz_id: str | None = None` parameter. If
  provided, it is threaded through to each `MCQGenerator.generate` call and
  stored on the resulting `AssessmentItem` before persistence.
- `tests/unit/test_lesson_graph.py` — **modify**: add a test asserting
  `AssessmentItem(quiz_id="q-1", ...)` is valid and `AssessmentItem(...)`
  without `quiz_id` defaults to `None`.
- `tests/unit/test_quiz.py` — **modify**: add a test that when `quiz_id` is
  passed to `SectionQuizGenerator.generate`, all resulting items carry it.
  Also test that `quiz_id=None` preserves existing behaviour.
- `docs/adr/0015-quiz-id-tracking.md` — **create**: document the decision,
  alternatives, and consequences.

## Depends on

T0c-r1.

## Acceptance

```
SCHEMA_CHANGE=1 uv run pytest --cov
uv run mypy
uv run ruff check .
```

All three exit 0. Coverage ≥ 93 %. Tests assert:
- `AssessmentItem.quiz_id` defaults to `None`.
- `SectionQuizGenerator.generate` passes `quiz_id` through to persisted
  items when one is supplied.
- `Database.get_items_by_quiz_id("q-1")` returns only items with that
  `quiz_id`.

## Out of scope

- Wiring Glows-Grows into the `POST /v1/attempts` response (T0c-r4).
- Changing the existing `Manual evaluation required` fallback behaviour for
  non-MCQ items (T13 decision preserved).
- Populating `quiz_id` on embedded MCQs generated outside a section quiz
  context (those items remain `quiz_id=None`).

## Risk notes

- The 7-file count slightly exceeds the nominal 6-file budget. The ADR is
  required by AGENTS.md for semantically significant schema changes; the two
  test-file edits are non-negotiable for coverage. Splitting the task further
  (e.g., separating the quiz.py wiring) would produce a single-file PR with
  no independent acceptance test — not worth the churn.
- `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` is SQLite-compatible as of
  SQLite 3.37.0 (2021). The project's `uv.lock` pins `aiosqlite>=0.22.1`,
  which requires Python 3.12 and therefore a recent-enough SQLite. If
  `Database._apply_schema` instead re-runs the full `schema.sql`, the column
  may already exist — use `IF NOT EXISTS` defensively.
- `MCQGenerator` currently takes a fixed signature; adding `quiz_id` as a
  keyword-only optional argument (`quiz_id: str | None = None`) avoids
  breaking existing callers.
