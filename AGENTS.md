# Agent guidance

Canonical orientation for any AI coding agent working in this repo
(Claude Code, Codex, etc.). `CLAUDE.md` imports this file.

This is a self-hosted, single-user replica of Google's Learn Your Way
(text and visual feature set). Turns a source PDF into a personalized,
multimodal, assessment-driven study experience.

See `docs/00-goals.md` for scope and `specs/` for the phase contract.

## Hard rules

- Source fidelity: every generated sentence must trace to source spans
  in the canonical lesson graph. No exceptions.
- No illustration generation in phases 1-3. Reliable educational
  illustration generation requires a fine-tuned domain model and a
  verifier layer; both are out of scope until a later phase.
- Modes are not independent. All modalities derive from the canonical
  lesson graph, never directly from the raw PDF.
- Edits to `src/lesson_graph/models.py` require `SCHEMA_CHANGE=1` in
  the agent environment. The schema is enforced as an invariant by
  the PreToolUse hook in `.claude/settings.json`.
- Unit tests must stay fast and model-free: mock `DocumentConverter.convert`
  and any Ollama/network call. Real inference belongs in `tests/integration/`
  behind `@pytest.mark.integration`.

## Tech (pinned)

- Base instructional model: Gemma 4 via Ollama (default) or any
  OpenAI-compatible API
- Document parsing: Docling
- Pipeline orchestration: Haystack
- Vector store: Qdrant (Docker)
- BM25: Haystack `InMemoryBM25Retriever`
- Reranker: sentence-transformers cross-encoder
  (`ms-marco-MiniLM-L-6-v2`)
- Web framework: FastAPI
- Job queue: Arq (Redis-backed)
- Database: SQLite
- File storage: local filesystem under a configurable data directory
- Config: pydantic-settings
- Logging: structlog
- Mind maps: Mermaid (generated source) + Cytoscape.js (interactive UI)

Rationale for each choice lives in `docs/adr/`.

## Development workflow

- Lint and format: `ruff` (configured in `pyproject.toml`).
- Type check: `mypy --strict`.
- Tests: `pytest` with coverage (93% gate, `fail_under = 93` in `pyproject.toml`).
- CI: `.github/workflows/ci.yml` — runs ruff, mypy, pytest, coverage on
  every push and PR.

Quick commands:

```bash
# First-time setup in a fresh checkout / worktree — installs dev
# tooling (ruff, mypy, pytest-cov) declared in
# [project.optional-dependencies].dev. Required before any of the
# commands below; without it `uv run ruff` / `uv run mypy` fail with
# "Failed to spawn".
uv sync --extra dev

uv run ruff check .                # lint
uv run ruff format .               # format
uv run mypy                        # type-check
uv run pytest --cov                # unit tests + coverage (CI command)
uv run pytest -m integration       # integration tests (needs Docker + Ollama)
uv run pre-commit run --all-files  # run all pre-commit hooks

# Run the full backend stack (API + worker + all backing services):
docker compose up                            # single command — starts all services
docker compose up --build                    # rebuild Python image after dep changes
pnpm --dir web dev                           # Vite dev server (port 5173, proxies /v1 → 8000)

# Run services locally (without Docker, for rapid iteration on the Python layer):
uvicorn lyw_core.api.app:app --reload        # FastAPI JSON API + SPA static serving (port 8000)
arq lyw_core.worker.settings.WorkerSettings  # Arq ingest worker (needs Redis)
python -m lyw_core inspect <pdf>             # parse PDF, print concept tree

# Fallback for one-off invocations without touching .venv:
uvx ruff check .
uvx --with pydantic mypy src/      # mypy needs the pydantic plugin
```

## Working agreement

- Each PR must reference a spec file in `specs/` and update the
  matching plan in `docs/plans/` if one is in flight.
- Schema changes require `SCHEMA_CHANGE=1`, an updated test in
  `tests/unit/test_lesson_graph.py`, and an ADR if the change is
  semantically significant.
- Phase 3 generators must persist output via the two-store pattern in
  ADR-0013: file content is written to content-addressed storage via
  `DataDir.write_asset(data, suffix=...)` (SHA-256 over bytes); metadata
  is keyed in the `derived_assets` SQLite table by
  `(lesson_id, concept_id, kind, profile_id)`. The `personalize_concept`
  Arq job orchestrates both writes; generators must not call
  `save_derived_asset` directly.
- There are two `DerivedAsset` types: `lesson_graph.models.DerivedAsset`
  (Pydantic, generator-output domain model with `based_on_concepts` and rich
  `personalization_profile`) and `lyw_core.db.dao.DerivedAsset` (plain
  dataclass, persistence record with scalar `concept_id` and `file_path`).
  Generators construct the Pydantic model; the Arq job derives the DAO record
  from it before persisting. Do not conflate them.
- Lesson-level generator kinds (`mind_map`, `timeline`) use sentinel constant
  `LESSON_SCOPED_CONCEPT_ID` (`"__lesson__"`) from `src/lyw_core/db/dao.py`
  as the `concept_id` value — the `derived_assets` table requires a non-null
  `concept_id`.
- Phase 3 generators that produce batches should discard failing items
  (as `MCQGenerator` does); generators that produce a single result
  should raise on failure (as `MnemonicGenerator` does). See ADR-0011.
- `PersonalizationProfile` is a Pydantic `BaseModel`; use the Pydantic
  constructor, not dict literals (ADR-0009).
- `AssessmentItem.concept_id` must be populated at generation time; it
  is not backfill-able via span join (ADR-0010).
- Serialise `GlowsGrows` with `dataclasses.asdict()`, not `.model_dump()`.

## Packages

- `src/lesson_graph` — domain models (LessonGraph, ConceptNode, AssessmentItem, …). No external services.
- `src/lyw_core` — ingest pipeline, personalization, generators, FastAPI JSON API, Arq workers, SQLite DAO, settings. Serves the built SPA as static files in production.
- `web/` — full pipeline test UI (React 18 + Vite + TypeScript + TanStack Query/Router). Dev: `pnpm --dir web dev` on port 5173 (proxies `/v1`, `/healthz`, `/openapi.json` to FastAPI). Prod: `pnpm --dir web build` → FastAPI mounts `web/dist/` at `/` with SPA fallback.

New feature areas that are purely presentation (browser UI) go in `web/`. New feature areas that are API, worker, or domain logic go in `src/lyw_core/` or a new `src/lyw_<area>/` package. Never add HTML/templates/JS to `src/lyw_core/`.

## Phases

1. Ingest and ground (`specs/phase-1-ingest.md`) — complete
2. Personalization and assessment (`specs/phase-2-personalization.md`) — complete
3. Modality generators (`specs/phase-3-modalities.md`) — **in flight**

Plans for the in-flight phase live under `docs/plans/`. Specs are
stable contracts; plans are mutable trackers.

## Reference material

The original research document is preserved at
`docs/source/research-document.md` and the original PDF at
`docs/source/Building_an_Open-Source_Alternative_to_Google_s_Learn_Your_Way.pdf`.
The research document discusses topics outside this project's scope
(LTI, privacy, licensing, audio modalities). Working specs supersede
the research document on every point.

## Dependency Management

This project uses `uv` with `uv.lock` committed. Tooling configuration
lives in `pyproject.toml`.

There are two separate dev dependency groups with different purposes:
- `[project.optional-dependencies] dev` — CI tooling (`ruff`, `mypy`,
  `pytest`, `pytest-cov`). Not installed by default; activate with
  `uv sync --extra dev`. Required before running lint, type-check, or
  coverage locally.
- `[dependency-groups] dev` — local-only test helpers (`hypothesis`,
  `pre-commit`, `pytest-asyncio`, `syrupy`, `testcontainers`). Installed
  automatically by a plain `uv sync`.

When adding a Python dependency:
1. Runtime dep: `uv add <package>`
2. CI tooling: `uv add --optional dev <package>` (goes in
   `[project.optional-dependencies].dev`)
3. Local test helper: `uv add --group dev <package>` (goes in
   `[dependency-groups].dev`)
4. Commit the updated `pyproject.toml` and `uv.lock` together.

Run commands inside the env via `uv run <cmd>` (e.g. `uv run pytest`,
`uv run mypy`, `uv run ruff check`). `.venv/` is materialized lazily by
the first `uv run` invocation, but it only includes runtime deps and the
default `[dependency-groups].dev` set (hypothesis, pre-commit,
pytest-asyncio, syrupy, testcontainers). The tooling in
`[project.optional-dependencies].dev` (ruff, mypy, pytest-cov) is not
installed until you run `uv sync --extra dev`. Run that once per fresh
checkout or worktree.
