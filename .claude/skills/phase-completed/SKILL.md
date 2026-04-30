---
name: phase-completed
description: End-to-end phase wrap-up orchestrator. Use when the user says "phase N is done", "wrap up phase N", "close phase N", or "/phase-completed". Runs house cleaning, then spawns sub-agents for phase-retrospective, update-agents-md, reconcile-spec, and decompose-spec in the correct order. Auto-saves each artifact and presents one consolidated diff summary at the end for user review.
---

# Wrap up a completed phase

Orchestrate the full phase-close ceremony in one invocation: house
cleaning, retrospective, agent-file update, spec reconciliation, and
decomposition of the next phase. Each downstream skill runs as an
isolated sub-agent so it gets a clean context. All artifacts are
saved automatically; a single consolidated diff summary is presented
at the end for user review.

## Guards (check before any work)

1. If `.claude/STOP_LOOP` exists at repo root, abort: "Stopped by sentinel."
2. Run `which gh` — warn if missing (decompose-spec may reference GitHub URLs).
3. Run `git rev-parse --is-inside-work-tree 2>/dev/null` — must succeed. If not, abort: "Not inside a git repository."

## Determine the current phase N

N = the largest integer such that `docs/plans/phase-<N>-*-tracker.md`
exists. Concretely: `ls docs/plans/ | grep -oP 'phase-\K\d+(?=-.+-tracker)'` → take the max.

Validate:

- `specs/phase-<N+1>-*.md` must exist. If not, abort: "No spec found
  for phase N+1. Either this is the final phase or the spec has not
  been written yet."

## House cleaning (run interactively in main session)

Run these three checks in order. Any failure → stop and report.
Do not proceed to sub-agent invocations until all pass.

### 1. Tracker close-out audit

Read `docs/plans/phase-<N>-*-tracker.md`. Scan from the start of
the `## Tasks` section and stop at the next `## ` heading (avoids
false positives in `## Out-of-Spec Discoveries`). Every line in that
section must match `- [x]`. If any line matches `- [ ]`, abort and
list the unchecked tasks. There is no point retrospecting an
incomplete phase.

### 2. Pre-commit check

```bash
uv run pre-commit run --all-files
```

On non-zero exit: surface the output and stop. Most issues are
self-healing (ruff, whitespace fixers run automatically), so the
recovery path is to re-run and then re-invoke `/phase-completed`.

### 3. Git state checks (read-only)

```bash
git rev-parse --abbrev-ref HEAD     # must be "main"
git status --porcelain              # must be empty
git log origin/main..HEAD           # must be empty
git branch --merged main | grep -v '^\*\|main$'   # report; do NOT delete
```

Report any merged feat/T* branches found, but do not delete them.
(See memory: `feedback_branch_pruning.md`.)

If HEAD is not `main`, or status is dirty, or commits are un-pushed:
abort and report.

## Sub-agent invocations

Use the `Agent` tool with `subagent_type: "general-purpose"` for every
downstream skill. Do **not** use `Skill(...)` — that keeps the parent
context alive and defeats the purpose of clean-context isolation (see
`run-task/SKILL.md:107`).

### Step 1 — Phase retrospective (sequential; blocks steps 2+3)

Spawn one sub-agent:

```
Agent(
  subagent_type: "general-purpose",
  prompt: """
/phase-retrospective

Phase N=<N> has shipped. Generate the phase retrospective per the
skill's instructions at .claude/skills/phase-retrospective/SKILL.md.

IMPORTANT: this invocation is made from an orchestrator that
auto-saves all artifacts. OVERRIDE the skill's 'Do not save the file'
rule and write the completed retrospective directly to
docs/plans/phase-<N>-retrospective.md.

Return a one-paragraph summary of what you wrote (sections covered,
any open questions you flagged) so the orchestrator can include it in
the final consolidated diff summary.
"""
)
```

Wait for completion. Capture the returned summary. If the sub-agent
cannot produce a retrospective (e.g. reports missing or unresolved
tracker entries), surface the error and stop.

### Step 2 — `update-agents-md` + `reconcile-spec` (parallel)

Both depend only on the retrospective file saved in step 1. They
operate on different files (`AGENTS.md` vs. `specs/phase-<N+1>-*.md`).
Spawn both in **one message** (two `Agent` tool calls in parallel):

```
Agent(
  subagent_type: "general-purpose",
  prompt: """
/update-agents-md

Phase <N> retrospective was just written to
docs/plans/phase-<N>-retrospective.md. Update AGENTS.md per the skill's
instructions at .claude/skills/update-agents-md/SKILL.md.

IMPORTANT: this invocation is made from an orchestrator that
auto-saves all artifacts. OVERRIDE the skill's 'Do not save the file'
rule and apply the edits directly to AGENTS.md.

Return a summary listing every removal and every addition with a
one-line reason for each, plus the new line count.
"""
)

Agent(
  subagent_type: "general-purpose",
  prompt: """
/reconcile-spec

Reconcile specs/phase-<N+1>-*.md against decisions made in phases 1
through <N>. The latest retrospective is at
docs/plans/phase-<N>-retrospective.md. Follow the skill's instructions
at .claude/skills/reconcile-spec/SKILL.md.

IMPORTANT: this invocation is made from an orchestrator that
auto-saves all artifacts. OVERRIDE the skill's 'Do not save the file'
rule and apply the edits directly to the spec file.

Return the unified diff plus a list of citations (which retrospective
entry, ADR, or schema state drove each edit). List anything you
considered editing but did not, with reasons.
"""
)
```

Wait for both to return before launching step 3.

### Step 3 — `decompose-spec` (sequential; depends on step 2)

Decomposition reads the reconciled spec — must run after step 2's
reconcile-spec sub-agent has saved its edits.

```
Agent(
  subagent_type: "general-purpose",
  prompt: """
/decompose-spec

The phase-<N+1> spec at specs/phase-<N+1>-*.md was just reconciled
during this orchestration run; treat it as authoritative. Follow the
skill's instructions at .claude/skills/decompose-spec/SKILL.md.

IMPORTANT: this invocation is made from an orchestrator that
auto-saves all artifacts. OVERRIDE the skill's 'list any open questions
before the user saves' rule and write the artifacts directly:
  - docs/plans/phase-<N+1>-<slug>-tracker.md
  - docs/plans/phase-<N+1>/T*-*.md (one file per task)

Return a summary listing all T-numbers and a count of tasks, plus any
open questions the skill flagged for the user to resolve before
planning begins.
"""
)
```

## Consolidated diff summary

After all sub-agents return, produce one report for the user:

1. **Files created or modified** — list every path touched.
2. **`git diff --stat`** — run and embed the output.
3. **Open questions** — collect every open question returned by any
   sub-agent (especially decompose-spec, which routinely surfaces
   questions before the tracker is finalized).
4. **Recommended next step.** — "Review each artifact in your editor.
   When satisfied, commit the wrap-up in one commit:
   `git add docs/ specs/ AGENTS.md && git commit -m 'chore: close phase <N>, open phase <N+1>'`."

Do not commit. The user commits.

## Hard constraints

- Do not commit, push, or merge. This skill produces edits; the user
  commits.
- Do not delete branches. Honor `feedback_branch_pruning.md`.
- Do not modify `.claude/settings.json`, `src/lesson_graph/models.py`,
  any ADR, or the phase-<N+1> spec except via the reconcile-spec
  sub-agent.
- Do not run ruff / mypy / pytest separately. Pre-commit covers ruff;
  per-task CI is `run-task`'s responsibility.
- Do not retry failed sub-agents. Stop and surface the failure.
- Do not use `Skill(...)` to invoke downstream skills. Use `Agent`.

## See also

- `.claude/skills/run-task/SKILL.md` — the sub-agent invocation
  pattern this skill mirrors.
- `.claude/skills/phase-retrospective/SKILL.md`
- `.claude/skills/update-agents-md/SKILL.md`
- `.claude/skills/reconcile-spec/SKILL.md`
- `.claude/skills/decompose-spec/SKILL.md`
