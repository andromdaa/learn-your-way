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
- No recommender engine before phase 2 ships. Personalization is
  explicit-profile plus quiz feedback only.
- Edits to `src/lesson_graph/models.py` require `SCHEMA_CHANGE=1` in
  the agent environment. The schema is enforced as an invariant by
  the PreToolUse hook in `.claude/settings.json`.

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

- Package management: `uv`. Lockfile (`uv.lock`) is committed.
- Lint and format: `ruff` (configured in `pyproject.toml`).
- Type check: `mypy --strict`.
- Tests: `pytest` with coverage (90% gate).
- CI: `.github/workflows/ci.yml` — runs ruff, mypy, pytest, coverage on
  every push and PR.

Quick commands:

```bash
ruff check .                # lint
ruff format .               # format
mypy                        # type-check
pytest --cov                # tests + coverage
pre-commit run --all-files  # run all pre-commit hooks
```

## Working agreement

- Each PR must reference a spec file in `specs/` and update the
  matching plan in `docs/plans/` if one is in flight.
- Schema changes require `SCHEMA_CHANGE=1`, an updated test in
  `tests/test_lesson_graph.py`, and an ADR if the change is
  semantically significant.
- Do not add modality generators before phase 3 is opened.

## Phases

1. Ingest and ground (`specs/phase-1-ingest.md`)
2. Personalization and assessment (`specs/phase-2-personalization.md`)
3. Modality generators (`specs/phase-3-modalities.md`)

Plans for the in-flight phase live under `docs/plans/`. Specs are
stable contracts; plans are mutable trackers.

## Reference material

The original research document is preserved at
`docs/source/research-document.md` and the original PDF at
`docs/source/Building_an_Open-Source_Alternative_to_Google_s_Learn_Your_Way.pdf`.
The research document discusses topics outside this project's scope
(LTI, privacy, licensing, audio modalities). Working specs supersede
the research document on every point.

## NixOS environment

This machine runs NixOS with direnv + nix-direnv. The `flake.nix` dev
shell activates automatically on `cd` (after `direnv allow`), providing
nixpkgs-linked `ruff`, `mypy`, `precommit`, and `python312`.

Run tools directly — no `uv run` or `nix develop --command` prefix needed:

```bash
ruff check .
ruff format .
mypy
pytest --cov
```

Always launch `claude` from within this directory so the direnv
environment is inherited.

## Dependency Management

This project uses NixOS with Nix flakes. There is no uv, pip, or virtualenv.

When adding a Python dependency:
1. Do NOT use `uv add`, `pip install`, or any package manager CLI.
2. Find the package in nixpkgs at `https://search.nixos.org/packages` under `python313Packages.<name>`.
3. Add it to the `ps: with ps; [...]` list in `flake.nix`.
4. If the package does not exist in nixpkgs, say so and stop — do not attempt a workaround without being asked.

Dev dependencies (pytest, mypy, ruff, etc.) also go in the same list in `flake.nix`.
The `pyproject.toml` is for tooling configuration only (ruff, mypy, pytest settings). Do not add to its `[project.dependencies]`.
