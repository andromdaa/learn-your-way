---
name: start-phase
description: Decompose a phase spec from specs/phase-N-<name>.md into a tracker index plus per-task files under docs/plans/phase-N/. Use when the user says "start phase N", "open phase N", "decompose phase N", or otherwise indicates they are ready to begin a new phase. Produces a granular task breakdown (one branch, one PR, one session per task) with a spec-coverage table and a stable index file. Plan-only — does not write any implementation code.
---

# Start a phase

Use this skill when the user is ready to open a new phase of work. Each
phase corresponds to one spec under `specs/` and produces a tracker
index plus a directory of per-task files. Implementation does not begin
in this session — that is what `run-task` is for.

## Read first

Load these in full:

- `AGENTS.md`
- `docs/00-goals.md`
- `docs/01-architecture.md`
- `docs/02-data-model.md`
- `docs/03-stack.md`
- `docs/04-api.md`
- All files under `docs/adr/`
- `specs/phase-<N>-<name>.md`
- `pyproject.toml`
- `src/lesson_graph/models.py`
- `src/lesson_graph/interfaces/` (every file)
- `tests/test_lesson_graph.py`
- For phase 2 and beyond: every `docs/plans/phase-<M>-<name>-tracker.md` and the corresponding `docs/plans/phase-<M>/` directory for prior phases (read the index files and any task files whose deliverables this phase builds on)

Do NOT read `docs/source/` (research material; specs supersede it).

## Confirm understanding

Before producing the decomposition, list back:

- The phase's deliverables, in your own words.
- The spec's "out of scope" items, verbatim.
- Any deliverables in this phase that depend on outputs from a prior phase. Name the prior T-numbers.

If anything in the spec contradicts what you read in `AGENTS.md`, ADRs, or prior trackers, stop and surface the contradiction. Do not silently reconcile.

## Task granularity contract

Every task produced must satisfy all of the following:

- Diff fits in roughly 400 lines and at most 6 files touched.
- An agent does not need to read more than ~30K tokens of source to do it.
- Has a concrete acceptance test (a test file, a CLI command output, or a CI gate). Prose acceptance is not acceptable.
- Does not depend on any later T-number in the list.
- Does not violate `AGENTS.md` hard rules.

If a deliverable cannot be expressed as a single task within those bounds, split it. Common splits:

- Retrieval — BM25 only / Qdrant dense only / cross-encoder reranker (three tasks).
- Heuristic baseline before LLM-refined version.
- Schema change in its own task before any code that depends on the new field.
- Endpoint scaffolding before the integration that wires it to a job queue.

## Output structure

Produce two artifacts in this session:

### 1. The tracker index — `docs/plans/phase-<N>-<name>-tracker.md`

Roughly 80 lines. Sections in this order:

- `# Phase <N> — <name> tracker`
- One-paragraph status line.
- `## Tasks` — checkbox list, one line per task: `- [ ] T<N>: <one-line summary>` followed by a relative link to the task file.
- `## Decisions made` — empty placeholder.
- `## Open questions` — empty placeholder.
- `## Out-of-spec discoveries` — empty placeholder.
- `## Spec coverage` — markdown table mapping every bullet from the spec's "Deliverables" section to the T-numbers that cover it. No deliverable may be uncovered.

The index is the file most often read across the phase. Keep it small. Do not put task details here.

### 2. The task files — `docs/plans/phase-<N>/<T-number>-<slug>.md`

One file per task. Each file is 30-60 lines. Sections in this order:

- `# T<N>: <one-line summary>`
- `## Goal` — one paragraph. Why this exists as its own task.
- `## Files created or changed` — explicit list, by path. Distinguish "create" from "modify".
- `## Depends on` — prior T-numbers, or "none". Also list dependencies on prior phases by T-number.
- `## Acceptance` — concrete signal that the task is done. Prefer "test X passes" or "command Y produces output Z" over prose.
- `## Out of scope` — what the agent must not do in this task even if tempted. Be specific: name the things that look adjacent but belong to a later T-number.
- `## Risk notes` — optional. Pitfalls, prompt-iteration risk, dependency surprises. One or two bullets only when applicable. The "direct-compact" output style does not apply to this section — include reasoning, not just labels.

## Sequencing requirements

- Foundational, deterministic work first. Layout, types, deterministic baselines.
- Defer LLM-touching work until after deterministic baselines exist.
- Schema changes precede the code that depends on them.
- Real-service integration (Qdrant, Redis, etc.) follows in-process or fake-backed work.
- API endpoints come after the modules they wire together.
- Inspection or diagnostic surfaces come after the modules they inspect.

If a phase's spec deliverables can be ordered multiple ways, document the call in the task's "Risk notes" with the tradeoff. Do not pick silently.

## Hard constraints

- Do not write implementation code.
- Do not modify `specs/phase-<N>-<name>.md`. The spec is the contract; the tracker is mutable.
- Do not modify `AGENTS.md`, the schema, or any ADR. If the decomposition surfaces a need to amend any of these, list it under "Open questions" in the index.
- Do not propose new dependencies beyond what is already declared in `pyproject.toml` and the items the user has flagged for addition (`hypothesis`, `syrupy`, `testcontainers`, `pre-commit`). New dependencies surface as open questions, not decisions.
- Where you are uncertain about a sequencing choice, present the tradeoff in the relevant task's "Risk notes" rather than picking silently.

## Session output

Emit the index and every task file as separate fenced markdown blocks I can review and save. After the blocks, list any open questions you want resolved before I save them.

Do not save files yourself in this session. The user reviews each artifact, edits as needed (`Ctrl+G` opens any block in the editor), and saves manually. After review, the user may invoke this skill again with the resolutions to produce a revised set.