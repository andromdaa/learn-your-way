---
name: update-agents-md
description: Update AGENTS.md to reflect a phase's actual conventions, commands, and rules after a phase ships. Use whenever the user says "update AGENTS.md", "AGENTS.md is stale", "after phase N retrospective update AGENTS.md", or otherwise wants the agent-orientation file to match what the codebase actually expects. Edits AGENTS.md in place. Enforces the size budget and the "remove what is no longer true" discipline.
---

# Update AGENTS.md

Use this skill when AGENTS.md needs to be reconciled against what the codebase actually expects. Most commonly: after a phase ships, after a retrospective is written, or when the user has noticed AGENTS.md drifting.

AGENTS.md is loaded into every agent session. Every line costs tokens forever and competes for attention with every other line. Treat it like code: review it, prune it, do not let it grow indefinitely.

## Read first

Load these:

- `AGENTS.md` (the current state)
- `CLAUDE.md` (verify it still imports AGENTS.md correctly; should be `@AGENTS.md` or similar)
- The most recent phase retrospective at `docs/plans/phase-N-retrospective.md`
- `pyproject.toml` (commands and dependencies must match what AGENTS.md claims)
- `Makefile` or `justfile` if present (canonical command names)
- `.claude/settings.json` (defaultMode, hook behavior — AGENTS.md should not contradict the actual settings)
- `docs/adr/README.md` (the index — confirms ADRs AGENTS.md may reference still exist)
- The schema at `src/lesson_graph/models.py` (if AGENTS.md mentions schema invariants, they must still hold)

Do NOT load every ADR. Trust the index unless a specific ADR is referenced and ambiguous.

## Confirm scope

Before editing, list back to the user:

1. The current AGENTS.md line count.
2. Sections that appear stale (commands no longer correct, conventions superseded, hard rules contradicted by current code).
3. Sections that should be added based on the retrospective (new conventions established during the phase).
4. Sections to delete because the rule is now self-evident or has been superseded.

If the user's intent is unclear, ask. "Update AGENTS.md" can mean "add what's new" or "do a full pass and prune." These produce very different diffs.

## Hard size limits

- **Aim for under 200 lines.** Anthropic guidance and our own discipline.
- **Hard limit at 250 lines.** If the edit would push past 250, propose moves to nested CLAUDE.md files or to `docs/` with `@docs/...` references, rather than continuing to grow the root file.
- **No file exceeds the limit by accumulation.** If trimming is needed to fit a new addition, trim. Do not append-only.

## What belongs in AGENTS.md

Per Anthropic's published guidance and what we've established:

- Bash/`make` commands the agent could not guess.
- Code-style rules that differ from language defaults.
- Test runner choices and conventions.
- Branch/PR/commit conventions.
- Architectural invariants ("`domain/` does no I/O", "all DB access goes through repositories").
- Environment quirks.
- Non-obvious gotchas (the kind of "you would only know this if you've been bitten").
- Hard "do not" rules.

## What does NOT belong in AGENTS.md

- Anything the agent can infer from code.
- Standard Python conventions (PEP 8, "use type hints").
- Long API documentation — link out with `@docs/...`.
- Things that change weekly. Active feature plans go in `docs/plans/*.md`.
- File-by-file descriptions of the codebase.
- Self-evident exhortations ("write clean code").
- Praise, sentiment, or project-pitch language.

## Pruning rules

For every line in the current file, ask: "would removing this cause the agent to make a mistake?" If not, cut it.

Specifically prune:

- Rules contradicted by the current state of the code.
- Rules superseded by ADRs (replace with a reference to the ADR).
- Rules made redundant by hooks (`.claude/settings.json` enforces the rule mechanically; the AGENTS.md rule is documentation only — keep one or the other, not both).
- Sentences within a rule that elaborate without adding constraint.
- Multiple "do not" rules that overlap. Consolidate.

## Adding new rules

For every addition, ask: "is this a rule the agent would otherwise get wrong?" If the answer is "the agent would get this right by default," do not add it.

When adding:

- Match the file's existing voice and structure. Do not introduce new heading hierarchies.
- Place under the appropriate existing section (Hard rules, Tech (pinned), Working agreement, etc.). Do not create new top-level sections without justification.
- Keep each rule terse. One or two sentences. If a rule needs more explanation, link to the ADR or a `docs/` file.
- Reference ADRs and specs by full identifier ("ADR 0008", "specs/phase-2-personalization.md").

## Hard constraints

- Do not delete rules without flagging the deletion to the user. The user reviews every removal.
- Do not delete content from sections marked as canonical references (e.g. "Reference material" pointing to `docs/source/`).
- Do not modify `CLAUDE.md` unless its `@AGENTS.md` import is broken.
- Do not introduce praise, sentiment, or project-pitch language. The file is operational, not promotional.
- Do not pad rules to make them sound authoritative. Terse is correct.
- Do not add ALL CAPS emphasis to more than one or two genuinely load-bearing rules. Saturated emphasis stops working.

## Output format

Produce the edit as a unified diff or as a full proposed file shown in a fenced block, depending on the size of the change:

- **Small change (under ~10 lines added/removed):** Show the proposed edits as a unified diff fenced block.
- **Larger change (full pass, restructuring):** Show the full proposed file in a fenced block.

After the proposed change:

1. Report the new line count.
2. List every removal with a one-line reason.
3. List every addition with a one-line reason.
4. Flag any addition that pushes the file past 200 lines.

Do not save the file. The user reviews and approves the diff.

## Closeout (when the user approves)

After the user approves and saves:

1. Confirm `CLAUDE.md` still imports correctly. Verify with: `cat CLAUDE.md` shows `@AGENTS.md` (or equivalent).
2. Confirm a clean session loads the file. The user does this with `claude --model sonnet`, then `/context`. Memory files should stay under 5%. If it's at 8%+, AGENTS.md needs further pruning.

## See also

- `examples/post-phase-update.md` — typical update after a phase retrospective
- `examples/pruning-pass.md` — pure pruning pass when the file has grown unwieldy
