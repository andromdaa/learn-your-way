# T12 — Attempts SQLite Table, Attempts DAO, Gap Detector (TDD-strict)

## Status

- [ ] T12: Attempts persistence + gap detector

## Goal

Add an `attempts` table to the SQLite schema. Add `record_attempt` and
`get_profile_attempts` to the DAO. Build `GapDetector` in
`lyw_core/assessment/gap.py`.

Gap detection algorithm (rule-based, no vector lookup):

1. Load all attempts for the profile; filter to incorrect ones.
2. For the most recent incorrect attempt, look up the `concept_id`
   from `assessment_items`.
3. Retrieve the `ConceptNode` for that `concept_id` from the lesson
   graph.
4. Walk `concept.prerequisites` in list order (index 0 = highest
   priority, per the ADR-0012 docstring clarification) and return the
   first prerequisite `concept_id` for which the learner has no
   correct attempt.
5. If all prerequisites are mastered, or there are no prerequisites,
   or there are no incorrect attempts, return `None`.

TDD-strict: write each failing test before the implementation branch
that satisfies it.

## Files

- Modify `src/lyw_core/db/schema.sql` — add `attempts` table.
- Modify `src/lyw_core/db/dao.py` — add `AttemptRecord` type and
  attempt DAO methods.
- Create `src/lyw_core/assessment/gap.py`.
- Create `tests/unit/test_gap.py`.
- Modify `tests/unit/test_db.py` — add attempt DAO tests.

## Depends On

- T0c-r2 (`AssessmentItem.concept_id`).
- T1 (`profiles` table must exist for FK).
- T8 (`assessment_items` table must exist for FK; item DAO methods).

## Acceptance

- `attempts` table: `id TEXT PK`, `profile_id TEXT NOT NULL REFERENCES
  profiles(id)`, `item_id TEXT NOT NULL REFERENCES assessment_items(id)`,
  `response TEXT NOT NULL`, `correct INTEGER NOT NULL`, `attempted_at
  TEXT NOT NULL`.
- `AttemptRecord` dataclass: `id: str`, `profile_id: str`, `item_id:
  str`, `response: str`, `correct: bool`, `attempted_at: str`.
- `record_attempt(profile_id, item_id, response, correct) -> None`.
- `get_profile_attempts(profile_id: str) -> list[AttemptRecord]`.
- `GapDetector.next_concept(profile_id: str, lesson_graph: LessonGraph,
  dao: LywDao) -> ConceptNode | None`.
- TDD tests cover all algorithm branches: smoke test (failed item →
  unmastered prerequisite returned), all prerequisites mastered
  (returns `None`), no attempts (returns `None`), multiple failures
  (uses most recent incorrect attempt).
- `ruff check`, `mypy`, `pytest` all pass.

## Out of Scope

- Vector lookup or embedding-based similarity.
- Sequencing models or contextual bandits.
- Anything resembling a recommender engine.

## Risk Notes

- T12 touches `schema.sql` and `dao.py` which T8 also modified. T12
  must branch from main after T8 merges; the diff is purely additive.
- Priority order for prerequisites is list order (index 0 = highest),
  confirmed by the ADR-0012 docstring clarification on
  `ConceptNode.prerequisites`.
