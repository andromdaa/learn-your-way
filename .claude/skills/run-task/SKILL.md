---
name: run-task
description: Execute a single phase task from docs/plans/phase-N-tracker.md. Use whenever the user references a T-number (e.g. "do T1", "start T7", "run T3"). Loads only the relevant task file and the phase index, delegates planning to an Opus Plan subagent, then executes the plan autonomously through the full ship cycle (test → implement → push → PR → squash-merge → next T).
---

# Run a phase task

Use this skill when the user names a T-number from a phase tracker.

## Guards (check before any work)

1. Sentinel: if `.claude/STOP_LOOP` exists at repo root, abort with "Loop stopped by sentinel." and exit.
2. CLI: run `which gh` — if missing, abort with "Install gh first (e.g. `nix-env -iA nixpkgs.gh`), then run `gh auth login`."

## Read first

Load these and only these:

- `AGENTS.md`
- `docs/plans/phase-<N>-tracker.md` (the index)
- `docs/plans/phase-<N>/<T-number>-<slug>.md` (the task file)
- `specs/phase-<N>-<name>.md`
- Every file the task names under "Files created or changed"

Do NOT read other task files in the phase. Do NOT read full phase docs unless the task references them.

## Confirm understanding

Before planning, list the task's acceptance criteria back in your own words. If anything is ambiguous against what you read, ask one clarifying question and stop.

## Variant detection

Check the task file for these markers and adjust accordingly:

- **Schema change.** Task touches `src/lesson_graph/models.py`. Add `SCHEMA_CHANGE=1` to the `.claude/settings.json` `env` block before any edit; remove it during closeout. Plan must include: test update in `tests/test_lesson_graph.py`, ADR under `docs/adr/`, both in the same PR.
- **New dependency.** Task adds a library. Use `uv add <dep>` (never hand-edit pyproject.toml or uv.lock). Pin major version. Verify CI after lockfile update.
- **Real services.** Task uses Qdrant, Redis, or other external service. Integration tests marked `@pytest.mark.integration`. Unit tests must not require any service.
- **TDD-strict.** Task is purely deterministic (parsers, validators, pure logic). Commit failing tests before implementing; the test→impl→chore commit ladder is the gate, not human approval.

## Plan

Spawn a Plan subagent (`subagent_type: Plan`, `model: opus`) with the full task context from the files loaded above. Request:

- Files to create or modify, by path.
- The failing test that proves acceptance, written as the first artifact.
- Order of operations: tests first, then implementation, then verification.
- Exact verification commands (lint, typecheck, tests, coverage).
- "Do not touch" list of out-of-scope files.

Read the returned plan and proceed immediately. No approval gate.

## Execute

1. Create branch: `git fetch origin && git checkout -B feat/<T-number>-<slug> origin/main`
2. Write failing tests. Commit: `test(T<N>): failing tests for <short description>`
3. Implement. Commit: `feat(T<N>): <description>`
4. Run pre-flight (mirror CI exactly):
   ```
   uv run ruff check .
   uv run ruff format --check .
   uv run mypy
   uv run pytest --cov --cov-fail-under=90
   ```
   On red: fix forward, commit `fix(T<N>): <description>`, re-run. Cap at 2 fix attempts — if still red, abort the loop and surface the failure.

All commits carry the trailer:
```
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

## Hard constraints

- Do not implement anything outside this task's scope. Out-of-spec discoveries go in the phase index under "Out-of-spec discoveries"; continue.
- Do not modify `AGENTS.md`, the spec, the schema, or any ADR unless the task explicitly requires it.
- Do not weaken or skip existing tests.
- No files outside the "Files created or changed" list without explicit justification.

## Closeout

After pre-flight is green:

1. Tick the task checkbox in the phase index file (NOT the task file): `[ ]` → `[x]`.
2. Append a "Decisions made" entry: date, decision, and rationale (rationale required).
3. Commit: `chore(T<N>): tick T<N> complete, add decisions to phase-<N>-tracker`
4. Push and open PR:
   ```bash
   git push -u origin feat/<T-number>-<slug>
   gh pr create --title "T<N>: <title>" \
     --body "Covers spec deliverable: '<deliverable>'. See docs/plans/phase-N/T<N>-<slug>.md."
   ```
5. Squash-merge:
   ```bash
   gh pr merge --squash --delete-branch
   ```
6. Return to main:
   ```bash
   git checkout main && git pull --ff-only
   ```
7. Schema-change variant only: remove `SCHEMA_CHANGE=1` from the `.claude/settings.json` `env` block.

## Loop

After closeout, scan `docs/plans/phase-<N>-tracker.md` for the next unchecked task:

- Read the `## Tasks` section only — stop scanning at the next `## ` heading to avoid false positives in `## Out-of-Spec Discoveries`.
- Match the first line satisfying: `^- \[ \] \[(T\d+[a-z]?): ([^\]]+)\]\(([^)]+)\)`
- If found: run `/clear` to reset context, then re-invoke this skill with that T-number.
- If none: print "Phase <N> complete. <M> tasks shipped this run." and stop.

## Safety

- **Sentinel:** check `.claude/STOP_LOOP` at repo root before each iteration. `touch .claude/STOP_LOOP` from another terminal to halt between tasks.
- **Watchdog:** cap fix-forward at 2 attempts per task. Cap consecutive auto-tasks at 5 — re-invoke explicitly to continue beyond 5.
- **Never retry a failed task silently.** If a task aborts (CI cap exceeded, push failure, merge failure), stop the loop and leave the branch open for inspection.

## See also

- `examples/standard-task.md` — typical execution
- `examples/schema-task.md` — schema-change variant
- `examples/tdd-task.md` — TDD-strict variant
