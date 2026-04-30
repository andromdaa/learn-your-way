---
name: phase-retrospective
description: Write a phase retrospective at the end of a phase. Use when the user says "phase N is done", "write the phase-N retrospective", "wrap up phase N", or otherwise wants to capture what shipped, what changed, and what carries over. Produces a single markdown file at docs/plans/phase-N-retrospective.md with five fixed sections. The retrospective is authoritative input to the next phase's decomposition; treat it as a permanent record, not a status update.
---

# Write a phase retrospective

Use this skill when a phase has shipped (all spec deliverables landed, tracker checkboxes ticked, branch merged) and the user wants to capture the lessons before opening the next phase.

The retrospective is read by the planner during the next phase's decomposition. It is authoritative where it diverges from the original spec. Write it accordingly: precise, complete, and honest about what changed.

## Read first

Load these:

- `AGENTS.md`
- `specs/phase-N-<name>.md` — the spec as written at the start of the phase
- `docs/plans/phase-N-<name>-tracker.md` — the index, including its "Decisions made," "Open questions," and "Out-of-spec discoveries" sections
- All task files under `docs/plans/phase-N/` — their final state, especially their "Decisions made" entries
- `git log --oneline main` filtered to the phase's branches if accessible — confirms what actually shipped
- `pyproject.toml` — confirms which dependencies were added during the phase

Do NOT read prior-phase retrospectives unless they are explicitly referenced. The retrospective for phase N is about phase N.

## Confirm scope

Before writing, list back to the user:

1. The number of tasks that shipped vs. the number planned.
2. Any tasks that were split, merged, or renumbered during execution.
3. Schema changes that landed during the phase.
4. New dependencies added.
5. Carry-over items the prior retrospective named for this phase, and whether they were actually addressed.

If anything is unclear (e.g. a task box ticked but no merged PR), ask before writing. Do not assume.

## Output: a single file

Write `docs/plans/phase-N-retrospective.md` with exactly these five sections, in this order. No more, no fewer.

### `## What shipped`

Cross-check against the spec-coverage table in the tracker, not against memory or against the task list. Every spec deliverable: did it actually land? If a deliverable is partial or skipped, say so explicitly with the reason. Do not soften.

Format: prose paragraph, not a checkbox list. The tracker is the checkbox list; this section is the narrative.

### `## Decisions that changed the spec`

Anything in the tracker's "Decisions made" or "Out-of-spec discoveries" sections that the next phase needs to know. Convention changes, schema additions beyond the spec, validator behavior that diverges from the spec wording, server-side-only conventions established for a field. One paragraph per material change. Reference the originating task by T-number.

This is the section the next phase's planner reads most carefully. Be specific. "Added `provenance` field to `ConceptNode` (T7) so downstream code can distinguish heuristic from LLM-refined nodes; ADR 0008 records the rationale" is correct. "Made some schema improvements" is not.

### `## What was harder than expected`

Tasks that took two sessions instead of one. Tasks where the agent went off the rails. Tasks where the acceptance test was the wrong gate. Tasks where prompt iteration ran longer than the planning estimate. Be specific about what the failure mode was, not just that there was one.

This section is for the next phase to learn from. If LLM-driven tasks consistently took 3x the deterministic ones, say so — that informs how the next planner sizes similar tasks.

### `## What was easier than expected`

Where the discipline overshot. Sessions that closed in half the planned time. Tasks where the TDD-strict split was overkill. Tasks where the validator framework absorbed work that was scoped as separate.

The next planner uses this to right-size discipline. Without it, the project ossifies into ceremony that no longer earns its weight.

### `## Carry-overs`

A bullet list. Each item is one of:

- **Cleanup deferred from this phase to the next.** Things that should have shipped here but didn't, with the reason.
- **Technical debt accepted during this phase.** Shortcuts that were the right call in context but need to be addressed.
- **Deferred decisions that come due in the next phase.** Decisions explicitly punted forward (e.g. "Mnemonic persistence shape — defer to phase-3 planning").
- **Open questions still open.** Things the tracker's "Open questions" section never resolved.

Each bullet names the specific item, the reason it's a carry-over, and where it should land in the next phase if known.

## Hard constraints

- Do not write retrospective content for tasks that did not ship. If T11 was deferred, "T11 deferred" goes in carry-overs; do not write a retrospective entry as if it shipped.
- Do not soften failures. "We discovered late that the Docling parser misses character offsets on rotated pages and worked around it with a manual offset table" is correct. "We had some challenges with PDF parsing" is not.
- Do not add sections beyond the five named above. The format is fixed so the next planner knows where to look.
- Do not include praise, sentiment, or summary. The retrospective is a technical record.
- Reference task IDs (T-numbers) by full name. "T7" alone is acceptable in context; "T7 (LLM-refined chunker)" the first time it's mentioned.
- Reference ADRs by number. "ADR 0008" not "the provenance ADR."

## Output format

Output the full file content in one fenced markdown block, ready to save. After the block, list anything you couldn't determine without input — usually questions about whether a partial deliverable counts as shipped or carry-over.

Do not save the file. The user reads, edits, and saves.

## See also

- `examples/typical-retrospective.md` — a representative phase retrospective with all five sections populated
