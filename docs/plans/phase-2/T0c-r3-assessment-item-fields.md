# T0c-r3 — AssessmentItem.correct_answer + bloom_level + ConceptNode.prerequisites Clarification (ADR-0012)

## Status

- [ ] T0c-r3: AssessmentItem schema additions

## Goal

Add two nullable fields to `AssessmentItem` (**SCHEMA_CHANGE=1
required**):

1. `correct_answer: str | None` — stores the correct MCQ option text so
   `POST /attempts` (T13) can evaluate correctness by direct server-side
   comparison without a secondary lookup table.
2. `bloom_level: Literal["remember","understand","apply","analyze",
   "evaluate","create"] | None` — set by the MCQ generator prompt (T8);
   enables the active learning validator (T10) to identify
   application/analysis items precisely.

Also update the `ConceptNode.prerequisites` docstring to state that
list order is priority order (index 0 = highest priority). This is an
editorial change to the same file bundled here to minimise the number
of `SCHEMA_CHANGE=1` sessions.

Write ADR-0012 with one section per new field; mention the prerequisites
ordering convention in the ADR's Consequences section (it is a related
clarification, not a separate architectural decision).

## Files

- **Modify `src/lesson_graph/models.py`** (**SCHEMA_CHANGE=1 required**)
  — add `correct_answer: str | None = None` and `bloom_level:
  Literal[...] | None = None` to `AssessmentItem`; update the
  `ConceptNode.prerequisites` docstring.

- **Modify `tests/unit/test_lesson_graph.py`** — lock the new
  invariants with at minimum:
  - A positive test constructing an `AssessmentItem` with both fields
    set to non-`None` values and asserting round-trip serialization.
  - A negative test supplying an unrecognised `bloom_level` string and
    asserting `ValidationError`.
  - Confirmation that existing `AssessmentItem` tests still pass with
    `correct_answer=None` and `bloom_level=None` (the defaults).

- **Modify `docs/02-data-model.md`** — both new fields must appear in
  two places:
  1. The "Core types" code block (add the fields to the reproduced
     `AssessmentItem` class).
  2. The "Invariants" section (document that `correct_answer` is
     MCQ-specific and may be `None` for other item kinds; document that
     `bloom_level` drives the active learning validator and `None` is
     treated as `"remember"` by that validator).
  Also add a note in the "Core types" section or the `ConceptNode`
  block that `prerequisites` is ordered by priority (index 0 = highest).

- **Create `docs/adr/0012-assessment-item-fields.md`** — standard ADR
  shape (Status / Context / Decision / Consequences / Alternatives
  considered), two decision sections:
  - Section 1: `correct_answer` — why a field on the model rather than
    a separate table or out-of-band store.
  - Section 2: `bloom_level` — why a Literal enum rather than a
    free-text tag or a separate classification step.
  Consequences section must note: (a) `correct_answer` is
  MCQ-specific; other item generators may leave it `None`; T13 must
  handle `None` gracefully. (b) `bloom_level = None` is treated as
  `"remember"` by the active learning validator to avoid false passes
  on untagged items. (c) `ConceptNode.prerequisites` list order is now
  the canonical priority signal for the gap detector.

- **Audit `docs/04-api.md`** — `AssessmentItem` is absent from the
  OpenAPI component schemas (intentional: it is a domain model consumed
  internally, not returned by any endpoint). `correct_answer` does not
  belong in any response shape — the server evaluates it server-side
  and returns only `correct: boolean` to the learner in
  `AttemptFeedback`. `bloom_level` has no API surface relevance.
  `AttemptFeedback` and `AttemptRequest` require no changes.
  **No API surface change required. Audit recorded.**
  `correct_answer` is deliberately server-side only; any future endpoint
  exposing assessment data must construct a response model that omits it.
  Reuse of `AssessmentItem` directly in API responses is forbidden.

## Depends On

- T0c-r2 — `concept_id` must already be on `AssessmentItem`; T0c-r3
  adds to the same class and its tests build on T0c-r2's.

## Acceptance

- `AssessmentItem.correct_answer: str | None = None` — nullable; no
  non-empty constraint.
- `AssessmentItem.bloom_level: Literal["remember","understand","apply",
  "analyze","evaluate","create"] | None = None` — nullable; invalid
  string raises `ValidationError`.
- `ConceptNode.prerequisites` docstring updated: "Ordered by priority;
  the gap detector treats index 0 as the highest-priority prerequisite."
- `test_lesson_graph.py` covers: positive round-trip with both fields
  set; `ValidationError` on bad `bloom_level`; existing tests pass with
  both fields at `None` default.
- `docs/02-data-model.md` updated in both the code block and the
  Invariants section.
- `docs/adr/0012-assessment-item-fields.md` committed.
- `docs/04-api.md` unchanged; audit note above is the record.
- `ruff check`, `mypy`, `pytest` all pass.

## Out of Scope

- Setting `correct_answer` and `bloom_level` from the MCQ prompt (T8).
- SQL schema columns for the new fields (T8 adds `assessment_items`
  and will include `correct_answer TEXT` and `bloom_level TEXT`).

## Risk Notes

- Both fields default to `None` for backward-compatibility with any
  existing serialised `AssessmentItem` instances.
