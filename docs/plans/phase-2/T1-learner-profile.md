# T1 — LearnerProfile Model, Profiles SQLite Table, Profile DAO

## Status

- [ ] T1: LearnerProfile model, profiles table, profile DAO

## Goal

Define `LearnerProfile` as a Pydantic model in
`lyw_core/profiles/models.py`. Add a `profiles` table to the SQLite
schema. Add `add_profile`, `get_profile`, and `list_profiles` to the
DAO. This is the data layer that `POST /profiles` (T2) and the
personalization generators (T5, T7) consume.

`LearnerProfile` lives in `lyw_core`, not `lesson_graph`, because it
is application-level state — it does not represent canonical lesson
content and does not require `SCHEMA_CHANGE=1`.

## Files

- Create `src/lyw_core/profiles/__init__.py`.
- Create `src/lyw_core/profiles/models.py`.
- Modify `src/lyw_core/db/schema.sql` — add `profiles` table.
- Modify `src/lyw_core/db/dao.py` — add profile methods.
- Create `tests/unit/test_profiles.py`.

## Depends On

- None. Can run in parallel with T0c-r1, T0c-r2, and T3.

## Acceptance

- `LearnerProfile(id: str, grade_level: str, interests: list[str],
  goals: list[str])` Pydantic model; `grade_level` empty raises
  `ValidationError`.
- `profiles` table: `id TEXT PRIMARY KEY`, `grade_level TEXT NOT NULL`,
  `interests TEXT NOT NULL` (JSON array), `goals TEXT NOT NULL` (JSON
  array), `created_at TEXT NOT NULL`.
- `add_profile(profile)` upserts on `id`; `get_profile(id) ->
  LearnerProfile | None`; `list_profiles() -> list[LearnerProfile]`.
- Tests cover: add + retrieve round-trip; missing id returns `None`;
  empty `grade_level` raises; `interests` and `goals` survive JSON
  round-trip.
- `ruff check`, `mypy`, `pytest` all pass.

## Out of Scope

- `POST /profiles` endpoint (T2).
- Use of `LearnerProfile` by personalization generators (T5, T7).
- Profile deletion or versioning.

## Risk Notes

- `LearnerProfile.id` — single-user system, so an auto-generated UUID
  on `add_profile` (if caller omits it) is fine; decide at
  implementation time and document in the tracker decision log.
