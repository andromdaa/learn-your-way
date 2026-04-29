# T13 - Inspection CLI

## Status

- [ ] T13: Inspection CLI `python -m lyw_core inspect`

## Goal

Build the user-facing inspection surface required by the spec. The
command wires parser to chunker to renderer and prints the concept
tree with span anchors, learning objectives, and prerequisites. It is
parse-only orchestration with no new domain logic.

## Files

- Create `src/lyw_core/__main__.py`.
- Create `src/lyw_core/cli/__init__.py`.
- Create `src/lyw_core/cli/inspect.py`.
- Create `src/lyw_core/cli/render.py`.
- Create `tests/unit/test_cli.py`.
- Snapshot the subprocess output against the tiny fixture with syrupy.

## Depends On

- T9 for the LLM-refined chunker, with heuristic fallback if no
  `ModelClient` is configured.
- T6 for verifier-backed span display.

## Acceptance

- `uv run python -m lyw_core inspect tests/fixtures/tiny.pdf` exits 0.
- Output prints a tree with at least one concept node.
- `uv run pytest tests/unit/test_cli.py` passes.
- Snapshot output is stable and diffable.

## Out of Scope

- State mutation.
- Generation.
- API calls.
- Retrieval display.
- `--profile` or `--generate` flags.
- Any output that could violate the AGENTS.md hard rules.

## Risk Notes

- Keep output deterministic: sorted ids, no timestamps, no random
  values.
