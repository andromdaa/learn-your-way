---
name: reconcile-spec
description: Reconcile a future-phase spec against decisions made in completed phases. Use when the user says "reconcile phase N spec", "the spec is out of date with what shipped", "before opening phase N planning the spec needs to match the actual code", or otherwise wants the spec under specs/phase-N-*.md to reflect what prior phases actually decided. Edits the spec in place. The spec is the contract for the next phase's decomposition; this skill ensures the contract is honest before planning starts.
---

# Reconcile a phase spec

Use this skill after a phase retrospective has been written and before the next phase's decomposition begins. The retrospective surfaces decisions that diverged from what specs anticipated; the reconciliation propagates those decisions into the upcoming spec so the planner reads a contract that matches reality.

The spec is owned by the human, not the agent. The agent's role here is to surface what needs to change and propose specific edits; the human reviews and approves every change.

## Read first

Load these:

- `AGENTS.md`
- The spec to reconcile: `specs/phase-N-<name>.md`
- Every prior-phase retrospective: `docs/plans/phase-<M>-retrospective.md` for M < N
- Every prior-phase tracker INDEX: `docs/plans/phase-<M>-*-tracker.md` for M < N (read for the "Decisions made" and "Out-of-spec discoveries" sections)
- `docs/02-data-model.md` (for schema changes that may have invalidated spec language)
- `docs/04-api.md` (for API surface changes)
- All ADRs created during prior phases (use `docs/adr/README.md` to enumerate)
- The schema at `src/lesson_graph/models.py` (the actual current state)

Do NOT read prior-phase per-task files. The retrospective and tracker index are the right level of detail.

## Confirm scope

Before proposing edits, list back to the user:

1. Decisions from prior retrospectives that may affect the spec.
2. Schema additions or changes that may have invalidated specific spec language.
3. Convention shifts (package layout, fixture patterns, etc.) that the spec doesn't reflect.
4. Deferred decisions from prior planning that are now coming due in this phase.
5. ADRs created during prior phases that the spec should reference but doesn't.

For each candidate, name the specific section or sentence in the spec that's affected. Do not say "the spec is out of date"; say "section 3.2 says X, but ADR 0008 established Y."

If the user disagrees with a candidate or wants to defer a reconciliation, accept that. The spec belongs to the user.

## Reconciliation principles

- **Reconcile, don't rewrite.** The spec was carefully written. Most of it is still correct. Edit precisely; do not restructure.
- **Preserve the spec's voice.** The spec's tone, level of detail, and structure are deliberate. Match them.
- **Do not change scope.** Reconciliation aligns the spec with prior decisions; it does not add or remove deliverables. If the user wants a scope change, that's a separate decision and a separate edit.
- **Cite the source.** Every edit must trace to a specific retrospective entry, tracker decision, ADR, or schema state. If you can't cite the source, you're guessing — surface as an open question.
- **Preserve negation.** "Out of scope" and "do not" sections in the spec are load-bearing. Do not soften them; if anything, add to them.
- **Update cross-references.** If a schema change renamed a field or added a required field, every spec reference to that field must be updated.

## Common reconciliation patterns

These come up in nearly every reconciliation pass:

- **Schema additions.** Prior phases added fields to `ConceptNode`, `AssessmentItem`, or `DerivedAsset`. The spec references the schema but predates the additions. Update the spec's data-model references.
- **Server-side-only conventions.** A field is on the canonical type but must not appear in API responses (e.g. `correct_answer`). The spec's API section may need a callout.
- **Package layout.** The original spec assumed all code lives in one package; ADR 0006 split into `lesson_graph/` and `lyw_core/`. Spec references to file paths or import paths need updating.
- **Library-vs-integration timing.** Prior phases shipped certain features as library-only with worker integration deferred. The spec may describe end-to-end flows that are not yet wired; flag and update.
- **Validator framework references.** Phase 2 may have established a validator-framework abstraction; phase-3 spec language about "modality validators" should reference the framework, not describe it from scratch.
- **Deferred decisions surfaced as TODOs.** A prior retrospective may have deferred a decision that the upcoming spec needs to make. The spec should either name the decision explicitly or state that it's deferred to phase planning.

## Hard constraints

- Do not change the spec's deliverables list without explicit user approval. Reconciliation does not add or remove acceptance criteria.
- Do not change the "Out of scope" section without explicit user approval. If something is now in scope, that's a scope change, not a reconciliation.
- Do not delete content; edit in place. If a sentence is truly obsolete, propose deletion explicitly with reason.
- Do not "improve" the spec stylistically. Match the existing voice.
- Do not introduce ambiguity. Specs must be at least as precise after reconciliation as before.
- Do not propose edits that conflict with the canonical schema, an ADR, or a prior retrospective decision. The spec yields to those.

## Output format

Produce the reconciliation as a unified diff fenced block. Specs are usually large enough that diff format is more reviewable than reproducing the full file.

After the diff:

1. List every edit with: section/line affected, the source decision (retrospective, ADR, tracker entry, or schema state), and the rationale in one sentence.
2. List anything you considered editing but did not — and why.
3. List any open questions where you weren't sure whether to edit or defer to the user.

Do not save the file. The user reviews, approves, and saves.

## Closeout (when the user approves)

After the user approves and saves:

1. Confirm the edited spec still parses cleanly (no broken markdown, no orphaned references).
2. Suggest the user commit the spec edit on its own branch and PR, separate from any planning or feature work. Spec edits are reviewable artifacts.
3. Suggest opening the next-phase decomposition session in a fresh Claude Code session (`/clear` between reconciliation and decomposition — different cognitive contexts).

## See also

- `examples/post-phase-reconcile.md` — reconciling a phase-3 spec after phases 1 and 2 have shipped
