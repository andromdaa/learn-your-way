# T0c-r2 — temporal_position schema change on ConceptNode (ADR-0014)

## ID and one-line summary

T0c-r2: Add optional `temporal_position: int | None` to `ConceptNode` and write ADR-0014, so the timeline generator can identify chronologically ordered concepts.

## Goal

The phase-3 spec notes: "Timelines require chronological metadata on `ConceptNode`. If a source has no temporal structure, the timeline generator skips it." Currently `ConceptNode` carries no temporal field. Without one, the timeline generator (T3) cannot determine ordering or detect the skip condition.

This task adds `temporal_position: int | None = None` to `ConceptNode` in `src/lesson_graph/models.py`, updates the test suite and data-model docs, and writes ADR-0014 to explain the design. The field is optional with a `None` default so no existing serialised lesson graphs require migration. The ingest and LLM-refined chunker paths do not need to populate it in phase 3; the timeline generator simply skips any graph where all concepts have `temporal_position = None`.

This is a schema-change task and requires `SCHEMA_CHANGE=1` in the agent environment.

## Files created or modified

- `src/lesson_graph/models.py` — **modify** (`SCHEMA_CHANGE=1` required): add `temporal_position: int | None = None` to `ConceptNode`.
- `tests/unit/test_lesson_graph.py` — **modify**: add tests that (a) confirm a `ConceptNode` constructed without `temporal_position` defaults to `None`, (b) confirm a node with `temporal_position=3` round-trips correctly through Pydantic, and (c) confirm the field is absent from the serialised form of a node that uses the default (`None`).
- `docs/02-data-model.md` — **modify**: add `temporal_position` to the `ConceptNode` shape and explain its semantics (integer ordering for chronologically structured content; `None` = unordered).
- `docs/04-api.md` — **modify**: add `temporal_position` to the `ConceptNode` OpenAPI schema component (optional integer, nullable).
- `docs/adr/0014-temporal-position-field.md` — **create**: document the decision, alternatives, and consequences.

## Depends on

T0c-r1.

## Acceptance

```
SCHEMA_CHANGE=1 uv run pytest tests/unit/test_lesson_graph.py --cov=src/lesson_graph -q
uv run mypy
uv run ruff check .
```

All three commands exit 0. The new `temporal_position` tests pass. `mypy --strict` reports no errors (the field is typed `int | None = None`).

## Out of scope

- Populating `temporal_position` in the heuristic or LLM-refined chunker (that is T3's concern, or a later phase's).
- Changing the SQLite schema for the `concepts` table (the DAO stores concepts but does not currently query `temporal_position`; the timeline generator reads the in-memory graph). If a later task needs to query by temporal position, add the column then.
- Any other `ConceptNode` fields.

## Risk notes

- The guard-schema hook (``.claude/hooks/guard-schema.py``) blocks edits to `src/lesson_graph/models.py` without `SCHEMA_CHANGE=1`. The agent must set this in the environment before any edit attempt.
- `temporal_position: int | None = None` must appear after the existing required fields to avoid Pydantic ordering issues (fields with defaults must follow fields without). The existing `prerequisites` and `provenance` fields already have defaults, so appending after them is safe.
