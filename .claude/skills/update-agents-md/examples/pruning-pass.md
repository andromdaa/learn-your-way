# Example: Pruning pass

When AGENTS.md has grown past comfortable. Common after two or three phases. The file may be technically correct but dense enough that the agent stops paying attention to specific rules.

## When to do this

- AGENTS.md exceeds ~200 lines.
- `/context` reports memory files at 7%+ of the window.
- The agent has started missing rules that "are right there in AGENTS.md."
- A quarterly cycle (regardless of size).

A pruning pass is its own session. Do not combine with adding new rules; the cognitive load of "what to keep" is different from "what to add."

## Session start

```bash
git status
claude --model opusplan
```

## User opens with

> AGENTS.md is at 230 lines, do a pruning pass.

## Skill workflow

### 1. Read

Per SKILL.md "Read first." For a pruning pass, also load:

- All retrospectives under `docs/plans/` — confirm which rules are still load-bearing.
- The most recent few task files — confirm which rules the agent is actually using.

The goal is to identify rules that are technically true but no longer needed because the discipline has moved into hooks, schema, ADRs, or settled convention.

### 2. Confirm scope

> AGENTS.md is 230 lines. Pruning candidates I've identified:
>
> - 14 lines of phase-1-specific guidance ("phase 1 is foundational...", "ingest-only until...") — these were removed individually before but the section header and surrounding prose are still present.
> - 8 lines describing the synthetic-PDF fixture pattern. The pattern is now codified in `tests/AGENTS.md` (added during phase 2). Move the detail to that file; keep one line in root AGENTS.md.
> - 12 lines of "Working agreement" rules that describe the run-task skill's behavior. The skill enforces these; AGENTS.md repetition is redundant.
> - 6 lines of stack rationale that duplicate ADRs.
> - 4 lines of repetition between "Hard rules" and "Working agreement" — the same constraint stated twice.
>
> Estimated reduction: ~44 lines, taking the file from 230 to ~186.
>
> Anything you'd preserve from the candidates? Anything else you want pruned that I've missed?

User answers; the conversation may iterate.

### 3. Produce the proposed file

Because this is a large restructuring, the agent produces a full proposed file in a fenced block, not a diff. The user reads top to bottom.

The structure should match the current file's section order: Hard rules, Tech (pinned), Development workflow, Working agreement, Phases, Reference material. Do NOT introduce new top-level sections during a pruning pass.

### 4. Reporting

After the proposed file:

> New line count: 184 (was 230). Net −46.
>
> Major removals:
> - Phase-1 foundational guidance (14 lines) — phase 1 has long since shipped; the language has been stale across two phases.
> - Synthetic-PDF detail (7 lines) — moved to `tests/AGENTS.md`. One-line reference retained in root.
> - Run-task workflow description (12 lines) — handled by `.claude/skills/run-task/`. The skill is the authoritative description.
> - ADR-duplicating prose (6 lines) — references retained, rationale removed.
> - Cross-section repetition (~5 lines) — consolidated into single statements.
>
> Things I considered but kept:
> - The five-files-for-schema-change rule. It's documented in the run-task skill, but it's load-bearing enough that the duplication earns its weight. The user's discipline has caught planner errors against this rule three times in the visible history.
> - The "ALL CAPS sparingly" guidance is itself meta but it's preserved one of the actual ALL CAPS rules from getting saturated.
>
> One change I want to flag explicitly: the "Phases" section now has all three phase tracker references but no commentary about ordering. The `specs/` files are the contract; this section is just an index. If you want commentary, add it back deliberately.
>
> One question I held: there's a rule "Do not weaken or skip tests to make CI green." It's three places in the file (Hard rules, Working agreement, and an inline note in the testing section). I left all three because the rule is consistently violated by agents under pressure and the redundancy may be earning its weight. Confirm or trim.

User reviews. May ask for further trims or push back on specific removals. Agent iterates.

### 5. Closeout

After approval:

> Saved. New line count 184. Verify with `/context` in a clean session — Memory files should drop from ~7% to ~5%.
>
> Suggest scheduling the next pruning pass after phase 3 ships, or sooner if `/context` reports memory files above 6% again.

## What good pruning looks like

- File is shorter and reads more authoritatively. Fewer rules each carrying more weight.
- Every remaining rule is either a hard constraint, a non-obvious gotcha, or a convention the agent would otherwise miss.
- ADRs are referenced by number, not reproduced.
- Hooks are referenced where they enforce a rule mechanically; the AGENTS.md statement is informational only.
- No phase-specific guidance for completed phases.
- No praise, sentiment, project description beyond what oriented an agent to the task.

## Common mistakes during pruning

- **Removing rules the agent has been respecting silently.** Just because the agent isn't visibly violating a rule doesn't mean removing it is safe — the agent may be respecting it precisely because it's there. Keep load-bearing constraints.
- **Aggressive consolidation that makes rules ambiguous.** "Do not introduce new patterns when an existing one applies" is fine. Rolling that into "follow conventions" is too vague to enforce.
- **Removing rules that document behavior of automation the agent can't see.** If a hook blocks something, the rule documents the *why*. Keep at least the why.
- **Treating size as the goal.** The goal is signal density. A 250-line file of high-signal rules is better than a 150-line file with three vague rules in critical positions.
- **Adding new rules during a pruning pass.** Two separate sessions. The cognitive context is different.
