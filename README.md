# Learn Your Way OSS

Self-hosted, single-user replica of Google's Learn Your Way. Turns a
source PDF into a personalized, multimodal, assessment-driven study
experience while preserving source fidelity.

This repository is a planning scaffold. Implementation begins with
phase 1.

## Read first

- [`AGENTS.md`](./AGENTS.md) — orientation for AI coding agents
  (`CLAUDE.md` imports this).
- [`docs/00-goals.md`](./docs/00-goals.md) — scope and non-goals.
- [`docs/01-architecture.md`](./docs/01-architecture.md) — two-stage
  pipeline.
- [`docs/02-data-model.md`](./docs/02-data-model.md) — canonical lesson
  graph rationale.
- [`docs/03-stack.md`](./docs/03-stack.md) — pinned dependencies.
- [`docs/04-api.md`](./docs/04-api.md) — first-party API (OpenAPI 3.1
  stub).
- [`docs/adr/`](./docs/adr/) — architecture decision records.

## Phases

1. [`specs/phase-1-ingest.md`](./specs/phase-1-ingest.md) — ingest and
   ground.
2. [`specs/phase-2-personalization.md`](./specs/phase-2-personalization.md)
   — personalization and assessment.
3. [`specs/phase-3-modalities.md`](./specs/phase-3-modalities.md) —
   modality generators.

In-flight checklists for the active phase live under
[`docs/plans/`](./docs/plans/).

## Source material

The original research document driving these specs is preserved at
`docs/source/`.

## Development

```bash
uv sync --extra dev         # install dependencies (uses uv.lock)
uv run ruff check .         # lint
uv run ruff format .        # format
uv run mypy                 # type-check (strict)
uv run pytest --cov         # tests with coverage
```

The schema tests in `tests/unit/test_lesson_graph.py` exercise the
invariants documented in `docs/02-data-model.md`.

CI runs ruff, mypy, pytest, and a coverage gate on every push and
pull request.

## Schema changes

Edits to `src/lesson_graph/models.py` are blocked by a Claude Code
PreToolUse hook unless the agent runs with `SCHEMA_CHANGE=1` in its
environment. See `docs/02-data-model.md` for the full protocol.
