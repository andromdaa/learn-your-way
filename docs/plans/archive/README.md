# Archived Task Files

This directory contains task files for features that were cancelled or dropped as part of the Phase 2/3 scope reduction (ADR-0016).

## Why archived?

Per [ADR-0016 — Phase 2/3 scope reduction](../../../docs/adr/0016-phase-2-3-scope-reduction.md):

- **Phase 3** (modality generators: mind maps, timelines, slides) was cancelled entirely
- **Phase 2 assessment surface** (section quizzes, embedded MCQs, attempt recording, glows/grows feedback, mnemonics, gap detector) was dropped due to structural defects that were not contained by narrow fixes

The scope reduction preserves the earned bug-fix history in the main codebase (particularly in the `relevel` and `replace` paths that remain active), while eliminating the wider surface area that was paying interest on recurring defects.

## What's here

- `phase-3/` — all 10 task files for cancelled modality generators (T0c-r1 through r4, T1-T6)
- Dropped Phase 2 task files:
  - `T8-mcq-generator.md` — embedded MCQ generation
  - `T9-section-quiz.md` — section-level quiz generation
  - `T10-section-quality-validators.md` — quiz quality validation
  - `T11-mnemonic-generator.md` — mnemonic hint generation
  - `T12-gap-detector.md` — knowledge gap detection
  - `T13-assessment-api.md` — attempt recording and recommendations endpoints

## Historical record

These files remain in git history and serve as documentation of:

1. **Design decisions** — why these features were scoped, what problems they were meant to solve
2. **Implementation work** — architecture, API designs, and engineering choices from the phases
3. **Audit findings** — the defect patterns and lessons that informed the scope cut

Readers interested in why a feature was dropped, what was tried, or the overall system architecture should consult these files alongside the ADR.

## Related

- [ADR-0016 — Phase 2/3 scope reduction](../../../docs/adr/0016-phase-2-3-scope-reduction.md)
- [Phase 2 personalization spec](../../specs/phase-2-personalization.md) (now historical; superseded by ADR-0016)
- [Phase 3 modalities spec](../../specs/phase-3-modalities.md) (now historical; superseded by ADR-0016)
- [Phase 2 personalization tracker](../phase-2-personalization-tracker.md) (tracks active relevel/replace work only)
- [Phase 3 modalities tracker](../phase-3-modalities-tracker.md) (historical; superseded)
