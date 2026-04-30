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

- [x] [T0c-r1: PersonalizationProfile + ReplacementRecord schema change (ADR-0009)](phase-2/T0c-r1-personalization-profile-schema.md)
- [x] [T0c-r2: AssessmentItem.concept_id schema change (ADR-0010)](phase-2/T0c-r2-assessment-item-concept-id.md)
- [x] [T0c-r3: AssessmentItem.correct_answer + bloom_level + ConceptNode.prerequisites clarification (ADR-0012)](phase-2/T0c-r3-assessment-item-fields.md)
- [x] [T1: LearnerProfile model, profiles SQLite table, profile DAO](phase-2/T1-learner-profile.md)
- [x] [T2: POST /profiles endpoint](phase-2/T2-profiles-endpoint.md)
- [x] [T3: Validator framework — ValidationResult, Validator Protocol, gating (ADR-0011)](phase-2/T3-validator-framework.md)
- [x] [T4: Source faithfulness + clarity of learning intentions validators](phase-2/T4-item-validators.md)
- [x] [T5: Re-leveling generator (immersive text, snapshot tests)](phase-2/T5-relevel-generator.md)
- [x] [T6: Adaptability validator (readability scoring)](phase-2/T6-adaptability-validator.md)
- [x] [T7: Example replacement generator (snapshot tests)](phase-2/T7-example-replacement.md)
- [x] [T8: Embedded MCQ generator + assessment_items persistence](phase-2/T8-mcq-generator.md)
- [ ] [T9: Section quiz generator + Glows/Grows feedback (snapshot tests)](phase-2/T9-section-quiz.md)
- [ ] [T10: Coverage, emphasis, active learning section-quality validators](phase-2/T10-section-quality-validators.md)
- [ ] [T11: Mnemonic generator (snapshot tests)](phase-2/T11-mnemonic-generator.md)
- [ ] [T12: Attempts SQLite table, attempts DAO, gap detector (TDD-strict)](phase-2/T12-gap-detector.md)
- [ ] [T13: POST /attempts + POST /recommendations/next endpoints](phase-2/T13-assessment-api.md)

## Decisions Made

- 2026-04-30 T0c-r1: Used Pydantic BaseModel for PersonalizationProfile instead of TypedDict (as mentioned in docs/02-data-model.md). Rationale: TypedDict cannot enforce the non-empty justification invariant on ReplacementRecord; Pydantic field_validator provides construction-time enforcement. See ADR-0009.
- 2026-04-30 T0c-r3: Retroactively marked complete. AssessmentItem.correct_answer, bloom_level, and ConceptNode.prerequisites priority ordering were shipped in commit c1ad09e before the tracker was opened. ADR-0012 was committed in that session.
- 2026-04-30 T0c-r2: concept_id stored as a denormalised field on AssessmentItem rather than derived via source_span join. Rationale: gap detector queries it on every submission (O(1) vs join); runtime resolution of concept_id to a ConceptNode is the clarity validator's job (T4), not a model invariant.
- 2026-04-30 T1: LearnerProfile.id is a required caller-supplied string (not auto-generated in the model). Rationale: T2 (POST /profiles) will generate the UUID at the API layer; keeping id required keeps the model simple and lets tests control ids explicitly.
- 2026-04-30 T2: grade_level validated in CreateProfileRequest (not deferred to LearnerProfile construction). Rationale: validation errors in the handler body return 500; FastAPI only converts pydantic errors raised during request parsing to 422. Duplicating the validator on the request model keeps HTTP semantics correct.
- 2026-04-30 T3: Used Protocol structural typing over ABC inheritance for Validator[T]. Rationale: concrete validators (T4, T6, T10) need not inherit from a base class; structural typing keeps them independently testable. run_validators uses collect-all semantics (not fail-fast) so generators see the complete failure set in one call.
- 2026-04-30 T4: ItemValidationPayload defined in faithfulness.py (imported by clarity.py). Rationale: no additional types.py file needed; clarity is a consumer of faithfulness's payload definition, keeping the module count within the task's stated file list. span_is_contained uses both page-overlap and character-containment checks as specified in the risk notes.
- 2026-04-30 T5: Faithfulness gating is performed by constructing a synthetic AssessmentItem (kind=short_answer, source_spans=[original_span]) and running SourceFaithfulnessValidator on it. Rationale: reuses the T4 validator without adding a new validator type; the check verifies the replacement span is valid within the lesson graph. ReLeveler.relevel() is async to match ModelClient.complete().
- 2026-04-30 T6: Pass condition is strictly closer (rel_dist < orig_dist) OR already at target (orig_dist == 0). Rationale: equal-distance counts as failure because the prompt asked to re-level but produced the same relative distance — that signals the model didn't improve the text. textstat.flesch_kincaid_grade is called twice (original then releveled) to allow deterministic mocking via side_effect in tests.
- 2026-04-30 T8: MCQGenerator takes validators as Sequence[Validator[ItemValidationPayload]] and iterates them manually (not run_validators) so items that fail are discarded rather than raising ValidationError. assessment_items.source_spans stored as JSON array (same serialisation pattern as existing source_spans table). ORDER BY rowid used for insertion-order retrieval without a created_at column.
- 2026-04-30 T7: original_span is always concept.source_spans[0] for all replacements. Rationale: the model operates on text, not character offsets, so we cannot derive a more precise span from model output; using the first source span is the correct conservative anchor that keeps all replacements traceable to the source document. Faithfulness failures are discarded with structlog warning rather than raised so a partial model response does not abort the whole personalization run.

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

_(empty)_
