# T13 — POST /attempts + POST /recommendations/next Endpoints

## Status

- [ ] T13: Assessment and recommendations API endpoints

## Goal

Wire the attempts DAO and gap detector into FastAPI.

`POST /v1/attempts`: accepts `AttemptRequest(profile_id, item_id,
response)`, looks up the `AssessmentItem` by `item_id`, evaluates
correctness by comparing `response` to `item.correct_answer` (a direct
string comparison; set by T8's MCQ generator), calls `record_attempt`,
and returns `AttemptFeedback(correct, rationale, source_spans,
suggested_next_concept_id)`. Returns 404 if `item_id` not found.

`POST /v1/recommendations/next`: accepts `{profile_id, lesson_id}`,
loads the lesson graph, calls `GapDetector.next_concept`, and returns
`{next_concept_id, reason}` or `{next_concept_id: null, reason: "all
objectives mastered or no attempts recorded"}` when the detector
returns `None`.

Follow the T15 / T2 dependency injection pattern.

## Files

- Modify `src/lyw_core/api/app.py`.
- Modify `tests/unit/test_api.py`.

## Depends On

- T12 (attempts DAO, `AttemptRecord`, `GapDetector`).

## Acceptance

- `POST /v1/attempts`: 200 with `AttemptFeedback` on valid request;
  404 when `item_id` unknown; `correct` is `True` iff
  `response == item.correct_answer` (case-sensitive); TestClient tests
  cover both paths.
- `POST /v1/recommendations/next`: 200 with `next_concept_id` when a
  gap exists; 200 with `next_concept_id: null` when no gap; TestClient
  tests cover both.
- `ruff check`, `mypy`, `pytest` all pass.

## Out of Scope

- Glows/Grows in `AttemptFeedback` (no `quiz_id` tracking yet; note
  as a follow-on in the out-of-spec discoveries section when
  implemented).
- Authentication.
- Websocket subscription for async generation.

## Risk Notes

- Items with `correct_answer = None` (non-MCQ types) cannot be
  evaluated by direct comparison. The endpoint must return a sensible
  default (`correct: False`, `rationale: "Manual evaluation required"`)
  for such items rather than a 5xx. Decide at implementation time and
  record the decision in the tracker.
