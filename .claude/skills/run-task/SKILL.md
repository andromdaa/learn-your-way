---
name: run-task
description: Execute a single phase task from docs/plans/phase-N-tracker.md. Use whenever the user references a T-number (e.g. "do T1", "start T7", "run T3"). Loads only the relevant task file and the phase index, produces a plan-mode plan, gates on user approval before any edits, then executes with TDD discipline and required verification.
---

# Run a phase task

Use this skill when the user names a T-number from a phase tracker.

## Read first

Load these and only these:

- `AGENTS.md`
- `docs/plans/phase-<N>--tracker.md` (the index)
- `docs/plans/phase-<N>/<T-number>-<slug>.md` (the task file)
- `specs/phase-<N>-<name>.md`
- Every file the task names under "Files created or changed"

Do NOT read other task files in the phase. Do NOT read full phase docs unless the task references them.

## Confirm understanding

Before planning, list the task's acceptance criteria back in your own words. If anything is ambiguous against what you read, ask one clarifying question and stop.

## Variant detection

Check the task file for these markers and adjust accordingly:

- **Schema change.** Task touches `src/lesson_graph/models.py`. Requires `SCHEMA_CHANGE=1` in environment. Plan must include: test update in `tests/test_lesson_graph.py`, ADR under `docs/adr/`, both in the same PR.
- **New dependency.** Task adds a library. Use `uv add <dep>` (never hand-edit pyproject.toml or uv.lock). Pin major version. Verify CI after lockfile update.
- **Real services.** Task uses Qdrant, Redis, or other external service. Integration tests marked `@pytest.mark.integration`. Unit tests must not require any service.
- **TDD-strict.** Task is purely deterministic (parsers, validators, pure logic). Split into two prompts: write failing tests first, stop, await approval, then implement.

## Plan output

Produce a plan with:

- Files created or modified, by path. No additions beyond the task's "Files created or changed" without explicit justification.
- The failing test that proves acceptance, written as the first artifact.
- Order of operations: tests first, then implementation, then verification.
- Exact verification commands (lint, typecheck, tests, coverage).
- "Do not touch" list of out-of-scope files.

Stop after the plan. Wait for approval.

## Hard constraints

- Do not implement anything outside this task's scope. Out-of-spec discoveries go in the phase index under "Out-of-spec discoveries" with a T-number reference; continue.
- Do not modify `AGENTS.md`, the spec, the schema, or any ADR unless the task explicitly requires it.
- Do not weaken or skip existing tests.
- Commit at checkpoints: failing tests in, implementation green, full CI green. Branch: `feat/<T-number>-<short>`.

## Closeout

After the implementation passes:

1. Run the full local CI equivalent (`make ci` or the configured commands). Paste full output only if there are errors.
2. Tick the task checkbox in the phase index file (NOT the task file).
3. Append a "Decisions made" entry to the phase index with date, decision, and rationale. Rationale is required, not optional.

## See also

- `examples/standard-task.md` — typical execution
- `examples/schema-task.md` — schema-change variant
- `examples/tdd-task.md` — TDD-strict variant
