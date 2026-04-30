# Example: Reconcile phase-3 spec after phases 1 and 2 have shipped

The most common reconciliation pass: two prior phases shipped, multiple retrospectives have produced decisions, and the upcoming spec was written before any of them. Reconciliation aligns the spec with what's actually true.

## Session start

```bash
git status
claude --model opusplan
```

## User opens with

> Reconcile phase-3 spec.

## Skill workflow

### 1. Read

Per SKILL.md "Read first":

- `AGENTS.md`
- `specs/phase-3-modalities.md`
- `docs/plans/phase-1-retrospective.md`, `docs/plans/phase-2-retrospective.md`
- `docs/plans/phase-1-ingest-tracker.md`, `docs/plans/phase-2-personalization-tracker.md`
- `docs/02-data-model.md`, `docs/04-api.md`
- `docs/adr/README.md` and (selectively) the ADRs it indexes
- `src/lesson_graph/models.py`

Skip per-task files in `docs/plans/phase-1/` and `docs/plans/phase-2/`. The retrospectives are the right summary level.

### 2. Confirm scope

> The phase-3 spec was written before phases 1 and 2 shipped. Reconciliation candidates I've identified:
>
> Schema-level changes that affect the spec:
> - `ConceptNode.provenance` (ADR 0008, phase-1 T7) — phase-3 generators must set provenance values appropriately. The spec doesn't mention this.
> - `AssessmentItem.correct_answer` and `bloom_level` (ADR 0009, phase-2 T0c-r3) — phase-3 doesn't generate assessment items, but the slide generator may surface assessment-related context that interacts with these fields. Possibly no edit needed; flagging.
> - `personalization_profile` is now a `LearnerProfileTypedDict` (phase-2 cleanup) — phase-3 spec section on "Each generator consumes the personalized lesson graph" implicitly references this; the language is fine but a parenthetical reference would help the planner.
>
> Convention shifts:
> - Package layout: spec assumes generators live under `src/lesson_graph/generators/`. ADR 0006 split the package; generators belong under `src/lyw_core/generators/`. Multiple sentences in the spec need this update.
> - Fixture pattern: spec doesn't address test fixtures. Add a sentence pointing to the synthetic-PDF generator pattern established in phase 1.
>
> Deferred decisions coming due:
> - Mnemonic persistence shape (phase-2 Q4 deferral). Phase-3 spec doesn't mention mnemonics at all because mnemonics shipped in phase 2 as ephemeral. The deferred decision is "do mnemonics need a `DerivedAsset` entry now?" — this is a planning question, not a spec question, but the spec should at least name the deferral so the planner doesn't miss it.
>
> Library-vs-integration:
> - Phase 2 deferred Arq worker integration to phase 3. The phase-3 spec talks about asynchronous generation but doesn't acknowledge that the worker process and dispatch path are new in this phase. The spec can be more explicit.
>
> ADR references:
> - The spec references no ADRs. Worth adding ADR 0006 reference (package layout) where the spec discusses code organization.
>
> One thing I considered but want your call: the spec says "Generation may be retried with adjusted prompts" under Implementation notes. Phase 2 established a "reject, do not patch" pattern for validator failures. The spec language "retry with adjusted prompts" is consistent with that, but the wording is loose. Tighten to "Generation may be re-invoked with adjusted prompts; the rejected asset is discarded, not patched"? Or leave?
>
> Confirm the candidates and your call on the loose-language item.

User responds with confirmations and a tightening preference.

### 3. Produce the reconciliation diff

````
```diff
--- a/specs/phase-3-modalities.md
+++ b/specs/phase-3-modalities.md
@@ -10,6 +10,9 @@
 graph and produces `DerivedAsset` instances with full provenance.

+Generators live under `src/lyw_core/generators/` per ADR 0006.
+The schema package `src/lesson_graph/` carries only the canonical types.
+
 ## Order of work
@@ -35,7 +38,11 @@
 - [ ] Mind-map generator producing Mermaid diagrams from the concept
       graph.
+      Generator must set `DerivedAsset.based_on_concepts` and a
+      `personalization_profile` consistent with the
+      `LearnerProfileTypedDict` schema (see `docs/02-data-model.md`).
 - [ ] Timeline generator for chronological content. The lesson graph
       must record temporal ordering for this to be meaningful.
+      Whether `ConceptNode` requires a new field for chronological
+      ordering is a planning question; surface in phase-3 decomposition.
 - [ ] Slide generator producing structured slide decks with speaker
       notes. Source spans on every slide.
@@ -55,6 +62,11 @@
 - Cross-modality coherence beyond what the shared lesson graph
   provides.
 - Multi-language support. Phase 3 is English-only.
+- Mnemonic persistence shape was deferred from phase-2 planning
+  (`MnemonicResult` ships as ephemeral `lyw_core` data). Whether to
+  add a `mnemonic` kind to `DerivedAsset` is a phase-3 planning
+  decision, not a spec deliverable. The spec does not require
+  mnemonic persistence.

 ## Acceptance criteria
@@ -70,6 +82,11 @@
 - Asynchronous generation does not block interactive paths (quiz
   feedback, guided hints).

+Asynchronous generation requires the Arq worker process and the
+`POST /lessons/{id}/generate` dispatch path, both of which are new in
+this phase. Phase 2 shipped generators as library code only; phase 3
+wires them through Arq for the first time.
+
 ## Implementation notes

@@ -85,7 +102,7 @@
 - Each generator has its own validator. Validators run before the
   asset is persisted. A failed validation rejects the asset; it does
-  not patch it. Generation may be retried with adjusted prompts.
+  not patch it. Generation may be re-invoked with adjusted prompts;
+  the rejected asset is discarded, not patched.
```
````

### 4. Reporting

After the diff:

> Edits made:
>
> 1. **Goal section, package-layout note** — Source: ADR 0006. Rationale: the spec doesn't mention the package split; planner needs to know generators don't go under `lesson_graph/`.
>
> 2. **Mind-map deliverable, profile reference** — Source: phase-2 cleanup that introduced `LearnerProfileTypedDict`. Rationale: makes the typed-dict expectation explicit.
>
> 3. **Timeline deliverable, chronological-field note** — Source: phase-1 retrospective (`ConceptNode` schema as shipped). Rationale: surfaces a known schema-change candidate so the planner schedules it explicitly rather than discovering it mid-task.
>
> 4. **Out of scope, mnemonic deferral** — Source: phase-2 Q4 deferral. Rationale: deferred decisions must land somewhere durable; the spec is the right place for "this isn't required."
>
> 5. **Acceptance criteria, async wiring callout** — Source: phase-2 retrospective (Arq integration deferred). Rationale: the spec's "asynchronous generation" language implied it was already wired; reality is different.
>
> 6. **Implementation notes, retry-vs-patch tightening** — Source: your direction during scope confirmation.
>
> Considered but did not edit:
>
> - References to `AssessmentItem.correct_answer` and `bloom_level` — phase 3 doesn't generate assessment items, and the indirect references in the spec are all consistent with the schema as shipped. No edit needed.
> - The "Modalities in scope" list — unchanged. Spec deliverables are not modified during reconciliation.
> - The order-of-work strict ordering — unchanged. The constraint stands.
>
> Open questions:
>
> - The chronological-ordering field on `ConceptNode` may turn out to be a substantial schema change. The spec now flags it as a planning question, but if you'd rather pre-decide here ("yes, add a `temporal_position: int | None` field"), that would be a separate spec edit. I left it as a planning question for now.

### 5. Closeout

User approves; agent reminds:

> Saved. Suggest committing on its own branch:
>
> ```bash
> git checkout -b spec/phase-3-reconcile
> git add specs/phase-3-modalities.md
> git commit -m "spec: reconcile phase-3 spec against phases 1 and 2"
> gh pr create --title "Reconcile phase-3 spec post-phase-2" --body "..."
> ```
>
> After merge, `/clear` and start phase-3 decomposition in a fresh session.

## What good reconciliation looks like

- Every edit cites a specific source.
- Edits are surgical: small, traceable, additive where possible.
- The spec's voice and structure are unchanged.
- The "Out of scope" section is respected — additions only with explicit approval.
- Deferred decisions are surfaced where the planner will see them.
- Convention shifts (package layout) get explicit references to ADRs, not vague gestures.
- Loose language is tightened only when the user confirms.

## Common reconciliation mistakes to avoid

- **Restructuring the spec because "it would read better."** Reconciliation aligns; it does not redesign.
- **Adding deliverables from the retrospective.** If phase 2 surfaced a need that should be in phase 3, that's a scope change. Surface it as an open question; don't silently add it.
- **Removing "Out of scope" entries because they're "no longer relevant."** "No longer relevant" might mean "still right but irrelevant" — keep the negation. Removal requires explicit approval.
- **Editing the spec without a citable source.** Every edit traces to retrospective, tracker, ADR, or schema. If you can't cite, surface as an open question.
- **Tightening the spec's tone.** The spec's voice is the user's voice. Match it; don't improve it.
