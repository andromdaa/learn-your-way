# ADR-0016 — Phase 2/3 scope reduction: strip in place to relevel + replace + profile

**Status:** Accepted
**Date:** 2026-05-01
**Deciders:** Cole (project owner), Claude Opus 4.7 (agent)

## Context

The 2026-05-01 audit thread on [AND-21](mention://issue/417a7c9d-644e-41e8-a7e2-a67f729d159c)
and [AND-23](mention://issue/a8b9839f-6eab-4075-8b9a-c06cbb4912d2),
together with `docs/plans/audits/systemic-cleanup/`, documented a recurring
defect class across Phase 2 and Phase 3: eight closed PRs (#64, #66, #75,
#76, #77, #82, #83, #84) shipped narrow fixes that each held for the failure
mode they addressed, while the underlying *class* of failure kept resurfacing
in adjacent code paths (worker-result pickling, chunker-output chrome,
silent-empty replacement paths, modality validators).

The pattern is structural, not incidental. The current Phase 2/3 surface area
— modality generators, section-quiz / glows-grows feedback, attempt
recording, the full validator family — is wider than the project actually
needs to deliver its core value (a personalized study experience grounded in
the source PDF). Continuing to harden the wide surface is paying interest on
debt the project does not need to carry.

Two reshape options were weighed:

1. **Fresh start from end of Phase 1** — branch from the post-ingest cut and
   re-derive a smaller Phase 2 from there.
2. **Strip in place** — keep the relevel / replace / profile code paths that
   have already absorbed the audit's lessons, and delete everything else.

## Decision

**Drop Phase 3 modality generators entirely.** `mind_map`, `timeline`, and
`slides` generation, their validators, and the modality-specific pieces of
`personalize_concept` are removed. ADR-0010, ADR-0012, ADR-0014, and
ADR-0015 are superseded by this ADR.

**Drop most of Phase 2.** Removed: section quizzes, embedded MCQs, attempt
recording, glows/grows feedback, mnemonic generation, the gap detector, and
all assessment-item infrastructure. The `POST /attempts` and
`POST /recommendations/next` endpoints go with them.

**Kept from Phase 2:**

- Re-leveling (rewrite text to a target readability).
- Interest-based example replacement (replace personalizable spans with
  examples tied to learner interests).
- Learner profile data model and `POST /profiles`.
- `PersonalizationProfile` and `ReplacementRecord` (ADR-0009).
- The `personalize_concept` Arq job, restricted to `relevel` and `replace`
  kinds only.

**Kept ADRs:** ADR-0011 (validator framework) and ADR-0013 (DerivedAsset
two-store) survive but shrink — they will only be exercised by the relevel
and replace paths after this scope cut lands.

The execution shape is **strip in place**, not "fresh start from end of
Phase 1." This ADR is step 1 of a five-step sequence:

1. **(this ADR)** ADR + AGENTS.md scope-cut commit — no code change.
2. Phase 3 strip — delete `src/lyw_core/modalities/` and related.
3. Phase 2 partial strip + schema cleanup — delete
   `src/lyw_core/assessment/` and related; `SCHEMA_CHANGE=1`.
4. CI integration tier (Initiative 1 of `docs/plans/audits/systemic-cleanup/`)
   on the trimmed surface.
5. `JobOutcome[T]` (Initiative 2) plus post-strip abstraction simplification.

## Consequences

**Positive:**

- ~40-50% of `src/lyw_core` lines removed. Surface area for the recurring
  defect class shrinks proportionally.
- Initiatives 1 and 2 of `docs/plans/audits/systemic-cleanup/` land on a
  smaller, more stable target. Initiative 3 (chunker contract redefinition)
  retains its priority unchanged.
- The bug-fix history earned in relevel and replace (PRs #64, #66, #75,
  #76, #77, and friends) is preserved — strip-in-place keeps the lessons in
  place.
- [AND-16](mention://issue/df27d534-cac5-41af-86d5-3d9770175caf) becomes
  moot (it targets a Phase 3 generator that is being deleted).

**Kept-in-scope concerns:**

- [AND-21](mention://issue/417a7c9d-644e-41e8-a7e2-a67f729d159c),
  [AND-22](mention://issue/f253f879-c4cb-49d2-b4b9-143d2a91a723), and
  [AND-23](mention://issue/a8b9839f-6eab-4075-8b9a-c06cbb4912d2) remain in
  scope: relevel still calls `run_validators`; replace still raises
  `ReplaceSourceTooThinError`; both still call Ollama through the same
  paths the audit examined.

**Negative / accepted:**

- ADRs 0010, 0012, 0014, 0015 are superseded. Their decisions remain
  historically interesting but no longer constrain code.
- `specs/phase-2-personalization.md` and `specs/phase-3-modalities.md`
  become historical references (banner in step 1; deliverables strikethrough).
- **Forward-references** in other docs to deleted features will dangle after
  steps 2 and 3 of the sequence. Known sites include `docs/02-data-model.md`
  (assessment item invariants, modality `DerivedAsset.kind` values) and
  `docs/04-api.md` (the attempts and recommendations endpoints). These are
  **expected dangling references** that steps 2 and 3 of the strip sequence
  will resolve. They are intentionally not chased in step 1.
- The web frontend has parallel deletions wherever modality / quiz /
  attempt views render. Those deletions ride on steps 2 and 3, not step 1.
- The 93% coverage gate (`fail_under = 93` in `pyproject.toml`) is
  unaffected by step 1 (no code changes). Steps 2 and 3 will likely require
  the gate to be reassessed against the trimmed surface; that reassessment
  is out of scope here.

## Alternatives considered

### Fresh start from end of Phase 1

Branch from the post-ingest cut and rebuild Phase 2 from scratch. Rejected:

- Loses the earned bug-fix history in relevel and replace. PRs #64, #66,
  #75, #76, #77 each encoded a specific lesson; re-deriving them on a fresh
  tree would re-discover the same bugs.
- Higher cost than strip-in-place for no offsetting benefit. None of the
  audit's structural lessons (CI integration tier, typed worker results,
  chunker contract redefinition) require a fresh tree to apply — they apply
  to the strip-in-place tree just as well.
- Branch divergence: a parallel rebuild branch would conflict with every
  in-flight PR. Strip-in-place lands incrementally on `main`.

### Keep Phase 3, harden in place

Continue Phase 3 modality work and absorb the audit findings as Phase 3
matures. Rejected: this is what the project has been doing, and the
recurrence pattern documented in the audit (eight closed PRs, same defect
class, narrow fixes that hold but don't generalise) is the evidence it
isn't working at the current surface area.

### Keep Phase 2 assessment, drop only Phase 3

Preserve section quizzes, attempts, glows/grows, and the gap detector;
delete only modalities. Rejected: the assessment surface carries roughly
half of the audit-flagged complexity. Trimming Phase 3 alone would leave the
project still paying interest on most of the same debt.
