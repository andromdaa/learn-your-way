---
name: decompose-spec
description: Decompose a phase spec into single-session tasks. Use whenever the user asks to "decompose phase N", "plan phase N", "break down the phase-N spec into tasks", or otherwise wants to convert a spec under specs/ into a tracker plus per-task files under docs/plans/. Produces an index file (checkbox list, decisions, open questions, spec-coverage table) and one self-contained file per task. Plan only — no implementation code.
---

# Decompose a phase spec into tasks

Use this skill when the user wants to convert a stable spec at `specs/phase-N-<name>.md` into an executable plan: a tracker index at `docs/plans/phase-N-<name>-tracker.md` and one task file per task under `docs/plans/phase-N/`.

## Read first

Load these and only these:

- `AGENTS.md`
- `docs/00-goals.md`, `docs/01-architecture.md`, `docs/02-data-model.md`, `docs/03-stack.md`, `docs/04-api.md`
- Every file in `docs/adr/`
- The target spec at `specs/phase-N-<name>.md`
- Every prior-phase spec at `specs/phase-<M>-*.md` for M < N
- Every prior-phase tracker index at `docs/plans/phase-<M>-*-tracker.md` for M < N
- Every prior-phase retrospective at `docs/plans/phase-<M>-retrospective.md` for M < N (these are authoritative where they diverge from the prior spec)
- `docs/plans/README.md`
- `pyproject.toml`
- `src/lesson_graph/models.py` and `src/lesson_graph/interfaces/model_client.py`

Then list the directory tree of `src/lyw_core/` and `tests/` (top two levels). Phase N builds on what was actually shipped, not what the prior spec promised.

Do NOT read prior-phase per-task files under `docs/plans/phase-<M>/`. The index plus retrospective is the right level of detail for a planning session — full task histories are tens of thousands of tokens of noise.

## Confirm understanding

Before producing the plan, list back to the user:

1. The acceptance criteria from the target spec, in your own words.
2. Any explicit ordering constraints in the spec (e.g. phase-3 specifies a strict modality order).
3. Carry-overs from prior retrospectives that constrain this phase.
4. Deferred decisions from prior planning that this phase must resolve or explicitly defer again.
5. Persistence-and-deferral conventions from prior `T0c-r*` schema work that affect this phase.

If anything is ambiguous, ask before planning. Do not guess silently.

## Plan output

Each task must satisfy all of these:

- One branch, one PR, one Claude Code session.
- Diff fits in roughly 400 lines, at most 6 files touched.
- Agent reads at most ~30K tokens of source for the task.
- Concrete acceptance signal: test passing, command output, or CI gate. Not prose.
- No dependency on a later T-number.
- No violation of AGENTS.md hard rules.

For each task, produce:

- **ID and one-line summary.**
- **Goal.** One paragraph. Why this exists as its own task.
- **Files created or modified.** Explicit list, by path. Distinguish "create" from "modify."
- **Depends on.** Prior T-numbers, or "none."
- **Acceptance.** Concrete signal. Prefer runnable checks over prose.
- **Out of scope.** Specific things the agent must not do in this task, especially adjacent work that belongs to a later T.
- **Risk notes.** Pitfalls, prompt-iteration risk, dependency surprises. Omit if none.

## Sequencing rules

- **Carry-overs first.** Tasks addressing prior-retrospective debt and unresolved deferred decisions ship before any new feature work. Use `T0c-r<N>` numbering for these.
- **Schema changes are their own tasks.** Every schema change needs `SCHEMA_CHANGE=1`, a test update in `tests/test_lesson_graph.py`, an ADR under `docs/adr/`, and propagation to `docs/02-data-model.md` and `docs/04-api.md` (audit explicit even if no API change is needed). Schema-change tasks list at minimum five files in their "Files created or modified" section. Schema changes that touch fewer than five files are incomplete.
- **Library-first, integration second.** Generators ship as directly-callable functions before they get wired through Arq or any worker. Worker integration is its own task with its own acceptance test.
- **Validators are paired with their generators** unless the combined diff exceeds the granularity budget. Spec-mandated validators (gate persistence; reject, not patch) MUST gate persistence in their acceptance test.
- **API endpoints come last.** They wire previously built pieces. Wiring them early means integration-testing against vapor.
- **Async dispatch must be verified non-blocking.** Any worker integration's acceptance test asserts interactive paths respond while a generation job is in-flight. This is not optional — the spec wording ("does not block interactive paths") is a runtime claim that needs a runtime check.

## Hard constraints on this session

- Do not write implementation code.
- Do not modify the spec, `AGENTS.md`, the schema, or any ADR.
- Do not propose new dependencies beyond what is already in `pyproject.toml`. If a task needs one, surface as an open question, not a decision.
- Where a task may exceed the 400-line / 6-file budget, split it preemptively rather than flag it as a risk.
- Where you face a sequencing or scoping tradeoff, present it in the relevant task's "Risk notes" rather than picking silently. Be specific about what would change the call.

## Output format

Two artifacts:

1. **The tracker index**, suitable for saving to `docs/plans/phase-N-<name>-tracker.md`. Sections in this order: status, checkbox task list (one line per task), decisions made (empty), open questions (empty), out-of-spec discoveries (empty), spec coverage table mapping every bullet from the spec's "Deliverables" to T-numbers. No deliverable may be uncovered.
2. **Per-task files**, one per task, suitable for saving under `docs/plans/phase-N/<T-number>-<slug>.md`. Each is self-contained.

Output the index in one fenced block. Output each task file in its own fenced block, separated by headings the user can identify.

After the artifacts, list any open questions you want resolved before the user saves them. Do not answer your own questions; surface them.

## See also

- `examples/standard-decomposition.md` — typical phase decomposition end-to-end
- `examples/with-schema-changes.md` — phase containing schema-change tasks and their full propagation requirements
