# T4 - SQLite Schema, Migrations, and Source/Lesson DAO

## Status

- [ ] T4: SQLite schema, migrations, and source/lesson DAO

## Goal

Establish the relational store from ADR-0002 for the source registry
and lesson metadata. `POST /sources` and `GET /lessons/{id}` need a
place to persist rows before API work can land.

## Files

- Create `src/lyw_core/db/__init__.py`.
- Create `src/lyw_core/db/schema.sql` with initial `sources`,
  `lessons`, `concepts`, and `source_spans` tables.
- Create `src/lyw_core/db/dao.py` using async `aiosqlite`.
- Serialize and deserialize `LessonGraph`.
- Create `tests/unit/test_db.py` with in-memory SQLite.
- Modify `pyproject.toml` to add `aiosqlite`.

## Depends On

- T1 for `settings.db_path`.
- T2 because the data directory must exist.

## Acceptance

- `uv run pytest tests/unit/test_db.py` passes.
- A `LessonGraph` containing `ConceptNode`s with `SourceSpan`s`
  round-trips through the DAO unchanged.
- `uv run mypy` is strict-clean.

## Out of Scope

- `AssessmentItem` and `DerivedAsset` tables.
- Migration tooling beyond the bundled SQL file.
- Postgres shims.

## Risk Notes

- Decide whether `LessonGraph.concepts` is denormalized as JSON or
  stored as relational rows. Record the choice in the index decisions.
