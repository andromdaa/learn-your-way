# T2 — POST /profiles Endpoint

## Status

- [ ] T2: POST /profiles endpoint

## Goal

Wire `add_profile` from T1 into the FastAPI app as `POST /v1/profiles`.
Follow the T15 pattern: `Annotated[T, Depends(...)]` for dependency
injection; `create_app(lifespan=...)` factory for test isolation.

## Files

- Modify `src/lyw_core/api/app.py` — add `/v1/profiles` route.
- Modify `tests/unit/test_api.py` — add `POST /profiles` TestClient
  tests.

## Depends On

- T1 for `LearnerProfile` model and profile DAO.

## Acceptance

- `POST /v1/profiles` with a valid body returns 200 with the saved
  profile JSON.
- Missing `grade_level` returns 422.
- Duplicate `id` upserts cleanly (no 5xx).
- TestClient tests pass; `ruff check`, `mypy`, `pytest` all pass.

## Out of Scope

- Profile update semantics beyond upsert.
- Authentication.
- List-profiles or delete-profile endpoints.

## Risk Notes

- None.
