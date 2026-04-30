# Contributing

Learn Your Way is a self-hosted, single-user study-experience app built by
Cole Hoffman with AI coding agents (Claude Code, Codex, etc.). External
contributions are not expected, but the guidance below applies to all
contributors — human or agent.

## Where to start

Read [`AGENTS.md`](AGENTS.md). It covers the development workflow, tech stack,
hard rules, phases, and working agreement. Everything else here is a summary.

## Quick start

```bash
git clone <repo> && cd learn-your-way
uv sync --extra dev          # install runtime + CI tooling

uv run ruff check .          # lint
uv run ruff format .         # format
uv run mypy                  # type-check
uv run pytest --cov          # unit tests + coverage (90% gate)
uv run pre-commit run --all-files
```

## Opening a PR

- Branch off `main`, name it `<type>/<short-description>`.
- Every PR must reference a spec file in `specs/` (e.g. `specs/phase-2-personalization.md`).
- Update the matching plan in `docs/plans/` if one is in flight.
- CI must be green (ruff, mypy, pytest, coverage) before merging.
- Squash-merge; delete the branch after merge.
