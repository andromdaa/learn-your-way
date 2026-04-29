# T3 - Docker Compose for Qdrant and Redis with Health Check

## Status

- [ ] T3: `docker-compose.yml` for Qdrant and Redis with health check

## Goal

Stand up the two services required by ADR-0001 and ADR-0003: Qdrant
and Redis. Add a connectivity probe the stack and CI can use to
assert services are up.

## Files

- Create `docker-compose.yml` with pinned Qdrant and Redis image tags.
- Create `src/lyw_core/healthcheck.py` with async pings for Qdrant
  `/readyz` and Redis `PING`.
- Create `tests/unit/test_healthcheck_unit.py` with mocked `httpx`
  and mocked Redis, covering success and failure paths.
- Create `tests/integration/test_healthcheck.py` using
  `@pytest.mark.integration` and testcontainers.
- Modify `pyproject.toml` to add `httpx`, `redis[hiredis]`, and
  `qdrant-client` to runtime deps, and `testcontainers` to `dev`.
- Modify `.env.example` with Qdrant and Redis URL fields.

## Depends On

- T1, because service URLs come from settings.

## Acceptance

- `docker compose up -d` brings both services to a healthy state.
- `uv run python -m lyw_core.healthcheck` exits 0.
- `uv run pytest tests/unit/test_healthcheck_unit.py` passes without
  Docker.
- `uv run pytest -m integration tests/integration/test_healthcheck.py`
  passes with Docker.

## Out of Scope

- Index creation.
- Worker process.
- API container.

## Risk Notes

- Pin image tags explicitly; avoid `:latest`.
- Keep testcontainers tests behind the `integration` marker.
