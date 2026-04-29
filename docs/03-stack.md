# 03 — Stack

All choices are pinned. Rationale for the non-obvious calls lives in
`docs/adr/`.

## Core dependencies

| Concern | Choice | ADR |
| --- | --- | --- |
| Base instructional model | Gemma 4 via Ollama (default) or any OpenAI-compatible API | [0005](./adr/0005-ollama-first-model-serving.md) |
| Document parsing | Docling | — |
| Pipeline orchestration | Haystack | [0001](./adr/0001-haystack-over-vespa.md) |
| Vector store | Qdrant (Docker) | [0001](./adr/0001-haystack-over-vespa.md) |
| BM25 retrieval | Haystack `InMemoryBM25Retriever` | [0001](./adr/0001-haystack-over-vespa.md) |
| Reranker | sentence-transformers cross-encoder (`ms-marco-MiniLM-L-6-v2`) | — |
| Web framework | FastAPI | — |
| Job queue | Arq (Redis-backed) | [0003](./adr/0003-arq-over-celery.md) |
| Database | SQLite | [0002](./adr/0002-sqlite-over-postgres.md) |
| File storage | Local filesystem | [0004](./adr/0004-local-fs-over-s3.md) |
| Mind map generation | Mermaid | — |
| Concept graph (interactive) | Cytoscape.js | — |

## Application-level concerns

These are cross-cutting and pinned now to avoid ad-hoc choices during
phase 1.

### Configuration

**pydantic-settings.** All configuration is declared as a typed
`BaseSettings` subclass. Sources, in priority order:

1. Environment variables.
2. A `.env` file in the project root (gitignored).
3. Defaults declared on the settings class.

Settings cover at minimum: data directory path, SQLite database path,
Qdrant URL, Redis URL, model client selection (Ollama / Anthropic /
OpenAI-compatible), model name, Ollama base URL, API key (if a
remote client is selected).

`.env` is in `.gitignore`. A `.env.example` file ships the keys with
empty values once phase 1 begins.

### Logging

**structlog.** All log output is structured. Console rendering for
local development; JSON rendering when `LOG_FORMAT=json`. Bound
contextvars carry request-scoped fields (request id, lesson id,
profile id) so logs from generation jobs can be correlated with the
triggering API call.

Standard logging from third-party libraries (Haystack, FastAPI,
SQLAlchemy if used) is bridged into structlog via stdlib's
`structlog.stdlib` integration. No raw `print()` calls in
application code; ruff's `T20` rules can be enabled later if drift
becomes a problem.

### Asynchrony

The app process and the Arq worker are both async. SQLite access uses
`aiosqlite`; HTTP clients use `httpx`. There is no sync code path in
the application layer.

## Development tooling

| Concern | Choice |
| --- | --- |
| Package manager | `uv` with `uv.lock` committed |
| Python | 3.12+ |
| Linter / formatter | `ruff` |
| Type checker | `mypy` in strict mode, with the `pydantic.mypy` plugin |
| Test runner | `pytest` with `pytest-cov`, 90% coverage gate |
| CI | `.github/workflows/ci.yml` runs all of the above |

Quick commands:

```bash
uv sync --extra dev         # set up environment
uv run ruff check .         # lint
uv run ruff format .        # format
uv run mypy                 # type-check
uv run pytest --cov         # tests + coverage
```

## Runtime requirements

- Python 3.12 or newer
- Docker (for Qdrant and Redis)
- Ollama (if running the model locally) with Gemma 4 weights pulled
- Adequate disk space for source PDFs, derived assets, and the model
  weights if running locally

## Single-command bring-up

A `docker-compose.yml` is added in phase 1 that brings up Qdrant and
Redis. The app and worker run via `uv run` commands or a process
manager of the user's choice.
