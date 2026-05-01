# T0c-r4 — Glows-Grows in POST /v1/attempts response

## ID and one-line summary

T0c-r4: Wire Glows-Grows feedback into `POST /v1/attempts` by using the
`quiz_id` added in T0c-r3 to fetch sibling items and run the existing
`GlowsGrows` analysis.

## Goal

`POST /v1/attempts` currently returns `suggested_next_concept_id` (populated
by `GapDetector.next_concept` since PR #44) but no Glows-Grows feedback.
This task closes that gap.

When an attempt is recorded for an item whose `quiz_id` is non-`None`, the
handler:

1. Calls `db.get_items_by_quiz_id(item.quiz_id)` (added in T0c-r3) to fetch
   all sibling items in the same quiz.
2. Fetches recent attempts for those items via existing DAO methods to
   identify which concepts the learner answered correctly (Glows) and
   incorrectly (Grows).
3. Calls the existing `GlowsGrows` machinery in
   `lyw_core.assessment.quiz` to produce the structured feedback.
4. Serialises the result with `dataclasses.asdict()` (per the phase-2
   retrospective precedent) and returns it in the `AttemptFeedback` response.

When `quiz_id` is `None` (embedded MCQ, non-section-quiz attempt), the
response falls back to the current behaviour: `glows=None`, `grows=None`.

The `AttemptFeedback` response model in `attempts.py` gains two optional
fields: `glows: list[str] | None = None` and `grows: list[str] | None = None`.

## Files created or modified

- `src/lyw_core/api/routes/attempts.py` — **modify**: expand
  `AttemptFeedback` response model with `glows` and `grows` optional fields;
  add the quiz-id → sibling-items → Glows-Grows execution path inside the
  handler.
- `src/lyw_core/db/dao.py` — **modify**: add
  `get_attempts_by_quiz_id(quiz_id: str, profile_id: str) ->
  list[AttemptRecord]` so the handler can fetch sibling attempts efficiently
  without iterating all profile attempts.
- `tests/unit/test_api_attempts.py` — **modify**: add tests that:
  (a) an attempt on a quiz item (`quiz_id` set) returns non-null `glows` /
  `grows`; (b) an attempt on a non-quiz item (`quiz_id=None`) returns
  `glows=None, grows=None`; (c) the `Manual evaluation required` fallback for
  non-MCQ items is preserved.
- `tests/integration/test_attempts_glows_grows.py` — **create**: async
  integration test (mocked `ModelClient`, real in-memory SQLite via
  `Database.connect(":memory:")`) that exercises the full handler path:
  create a profile + lesson + items, record an attempt, assert `glows` and
  `grows` are populated. Mark with `@pytest.mark.integration`.

## Depends on

T0c-r3.

## Acceptance

```
uv run pytest tests/unit/test_api_attempts.py \
               tests/integration/test_attempts_glows_grows.py -v
uv run mypy
uv run ruff check .
uv run pytest --cov
```

All pass. Coverage ≥ 93 %. `POST /v1/attempts` for a quiz item returns
`AttemptFeedback` with non-null `glows` and `grows`. An attempt for a
non-quiz item still returns the current behaviour unchanged.

## Out of scope

- Changing the `Manual evaluation required` fallback for non-MCQ items
  (T13 decision preserved).
- Websocket or SSE push notifications (phase-4).
- Storing Glows-Grows results in the database; they are computed on demand
  per request.
- Any change to `GlowsGrows` dataclass fields or serialisation.

## Risk notes

- `GlowsGrows` is produced by calling the language model
  (`build_glows_grows_messages`). The handler therefore becomes async-LLM
  dependent on the Glows-Grows path. Mock `ModelClient.complete` in unit
  tests and the integration test; the real model call belongs behind
  `@pytest.mark.integration`.
- `get_attempts_by_quiz_id` requires joining through `assessment_items` on
  `quiz_id` then into `attempts` on `item_id`. If this query is complex,
  consider a two-step approach in the handler: fetch items by `quiz_id` (T0c-r3),
  then fetch attempts per item. Either is acceptable as long as tests confirm
  the correct sibling items are used.
- The `AttemptFeedback` response model change (adding `glows` / `grows`)
  is an additive, backward-compatible API change: existing callers that do
  not read those fields are unaffected.
