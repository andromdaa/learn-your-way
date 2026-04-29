# T1 - Settings, Logging, Runtime Dependency Manifest

## Status

- [ ] T1: Settings, logging, runtime dependency manifest

## Goal

Stand up the application-level cross-cutting concerns pinned in
`docs/03-stack.md`: `pydantic-settings` and `structlog`. Add the
dev-tooling spine with `pre-commit` and `.env.example`. Later tasks
should depend on a typed `Settings` object and configured logger
instead of deriving conventions independently.

## Files

- Create `src/lyw_core/settings.py` with a pydantic-settings
  `BaseSettings` using the `LYW_` prefix. Cover `data_dir`,
  `db_path`, `qdrant_url`, `redis_url`, `ollama_base_url`,
  `model_name`, and `log_format`.
- Create `src/lyw_core/logging.py` with `configure_logging()`.
- Create `.env.example`.
- Create `.pre-commit-config.yaml`.
- Create `tests/unit/test_settings.py`.
- Modify `pyproject.toml` to add `pydantic-settings` and `structlog`
  to runtime deps, and `pre-commit` to `dev` extras.

## Depends On

- T0c, because the `lyw_core` package must exist.

## Acceptance

- `uv sync --extra dev` resolves.
- `uv run pytest tests/unit/test_settings.py` passes, covering env
  prefix overrides, typed defaults, and `.env` discovery.
- `uv run pre-commit run --all-files` succeeds.
- `uv run mypy` and `uv run ruff check .` are clean.

## Out of Scope

- Filesystem layout, Docker services, and SQLite.
- Business logic.
- Imports of `docling`, `haystack`, `qdrant`, or `fastapi`.

## Risk Notes

- `pydantic-settings` v2 uses `SettingsConfigDict(env_prefix=...)`
  and `BaseSettings` from `pydantic_settings`.
- `structlog` config is global state; route through
  `configure_logging()` so tests can opt in cleanly.
