# Phase 2 Tracker — Personalization and Assessment

Compact index for Phase 2 task work. Detailed task files live in
`docs/plans/phase-2/`. The source contract remains
`specs/phase-2-personalization.md`.

## Status

Not started. Phase 1 acceptance criteria closed 2026-04-29; phase 2
opens now. T0c-r tasks address phase-1 carry-overs before any feature
task opens.

Each T-task is intended to be one branch, one PR, one agent session,
around 400 LoC, at most six files touched, no later T-numbers as
prerequisites.

## Tasks

- [ ] [T0c-r1: PersonalizationProfile + ReplacementRecord schema change (ADR-0009)](phase-2/T0c-r1-personalization-profile-schema.md)
- [ ] [T0c-r2: AssessmentItem.concept_id schema change (ADR-0010)](phase-2/T0c-r2-assessment-item-concept-id.md)
- [ ] [T0c-r3: AssessmentItem.correct_answer + bloom_level + ConceptNode.prerequisites clarification (ADR-0012)](phase-2/T0c-r3-assessment-item-fields.md)
- [ ] [T1: LearnerProfile model, profiles SQLite table, profile DAO](phase-2/T1-learner-profile.md)
- [ ] [T2: POST /profiles endpoint](phase-2/T2-profiles-endpoint.md)
- [ ] [T3: Validator framework — ValidationResult, Validator Protocol, gating (ADR-0011)](phase-2/T3-validator-framework.md)
- [ ] [T4: Source faithfulness + clarity of learning intentions validators](phase-2/T4-item-validators.md)
- [ ] [T5: Re-leveling generator (immersive text, snapshot tests)](phase-2/T5-relevel-generator.md)
- [ ] [T6: Adaptability validator (readability scoring)](phase-2/T6-adaptability-validator.md)
- [ ] [T7: Example replacement generator (snapshot tests)](phase-2/T7-example-replacement.md)
- [ ] [T8: Embedded MCQ generator + assessment_items persistence](phase-2/T8-mcq-generator.md)
- [ ] [T9: Section quiz generator + Glows/Grows feedback (snapshot tests)](phase-2/T9-section-quiz.md)
- [ ] [T10: Coverage, emphasis, active learning section-quality validators](phase-2/T10-section-quality-validators.md)
- [ ] [T11: Mnemonic generator (snapshot tests)](phase-2/T11-mnemonic-generator.md)
- [ ] [T12: Attempts SQLite table, attempts DAO, gap detector (TDD-strict)](phase-2/T12-gap-detector.md)
- [ ] [T13: POST /attempts + POST /recommendations/next endpoints](phase-2/T13-assessment-api.md)

## Decisions Made

_(empty — record decisions inline as they are made)_

## Open Questions

_(empty — record blockers and ambiguities here)_

## Out-of-Spec Discoveries

_(empty — record anything found during implementation that conflicts
with or extends `specs/phase-2-personalization.md`)_

## Spec Coverage

| `specs/phase-2-personalization.md` deliverable | Covered by |
| --- | --- |
| Learner profile data model and `POST /profiles` endpoint | T1, T2 |
| Re-leveling: rewrite to target readability, every change diffable | T5, T6 |
| Interest-based example replacement; never invent unanchored content | T7 |
| Embedded MCQs with rationale and source citation | T8 |
| Section-level quizzes (5–10 items) with Glows/Grows feedback | T9 |
| Mnemonic memory aids for high-priority concepts | T11 |
| Quiz signal capture and gap detector | T12 |
| `POST /attempts` and `POST /recommendations/next` | T13 |
| Schema change: `AssessmentItem.concept_id` (SCHEMA_CHANGE=1) | T0c-r2 |
| Schema change: `PersonalizationProfile` replacing `dict[str, Any]` (SCHEMA_CHANGE=1) | T0c-r1 |
| Pedagogy rubrics as validators gating persistence | T3 (framework), T4, T6, T10 |

## Architectural Artifacts

| Artifact | Task |
| --- | --- |
| ADR-0009: PersonalizationProfile schema | T0c-r1 |
| ADR-0010: AssessmentItem.concept_id | T0c-r2 |
| ADR-0011: Validator framework | T3 |
| ADR-0012: AssessmentItem.correct_answer + bloom_level | T0c-r3 |

## Pre-Task Open Questions

**Q1 — Readability library (blocks T6):** The adaptability validator
needs a readability score. Option A: add `textstat` as a runtime dep
(`uv add textstat`; add a `[[tool.mypy.overrides]]` suppression for
`textstat.*`). Option B: embed a minimal Flesch-Kincaid implementation
(~40 lines, no new dep, slightly inaccurate syllable counting via
vowel-run heuristic). Decide before T6 begins.

**Q5 — Personalization pipeline + Arq worker integration (shapes T5,
T7):** Do T5 and T7 stay as standalone library code (generators
callable directly, no Arq integration), or does phase 2 also wire them
into the existing `POST /lessons/{id}/generate` + Arq worker? The spec
is silent. Conservative reading: generators are library code in phase
2; worker integration is phase-3 work alongside slides/mind maps.
Confirm before T5 begins.
