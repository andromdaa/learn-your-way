# T15 - FastAPI Sources and Lessons Endpoints

## Status

- [ ] T15: FastAPI app: `POST /sources` and `GET /lessons/{id}`

## Goal

Implement the two phase-1 endpoints from `docs/04-api.md` end to end.
`POST /sources` accepts a multipart PDF upload, writes it through the
filesystem adapter, registers the `Source` row, enqueues ingest, and
returns 202. `GET /lessons/{id}` returns the persisted `LessonGraph`.

## Files

- Create `src/lyw_core/api/__init__.py`.
- Create `src/lyw_core/api/app.py`.
- Create `src/lyw_core/api/routes/sources.py`.
- Create `src/lyw_core/api/routes/lessons.py`.
- Create `tests/unit/test_api.py` using FastAPI `TestClient`.
- Modify `pyproject.toml` to add `fastapi`, `uvicorn[standard]`, and
  `python-multipart`.

## Depends On

- T2 for filesystem adapter.
- T4 for DAO.
- T14 for the ingest job.

## Acceptance

- `pytest tests/unit/test_api.py` passes with in-process ingest.
- `POST /sources` returns 202.
- `GET /lessons/{id}` returns a `LessonGraph` whose spans resolve.
- `/openapi.json` matches `docs/04-api.md` for these two routes.
- `mypy` is strict-clean.

## Out of Scope

- `/profiles`, `/lessons/{id}/generate`, `/attempts`, and
  `/recommendations/next`.
- Auth, rate limiting, and websockets.

## Risk Notes

- Keep the unit test self-contained by running ingest in-process.
- A real queue variant belongs in `tests/integration/test_api_e2e.py`.
