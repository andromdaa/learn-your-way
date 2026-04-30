# Phase 2 Retrospective

## What shipped

All nineteen spec deliverables from `specs/phase-2-personalization.md` landed.
The tracker is fully checked off: three carry-over schema tasks (T0c-r1 through
T0c-r3), two profile tasks (T1, T2), the validator framework (T3), four
validators (T4, T6, T10, and the faithfulness sub-check inside T5), three
generators (T5, T7, T11), the section quiz with Glows/Grows feedback (T8, T9),
and the gap detection and API endpoints (T12, T13). Sixteen PRs (#21–#35) were
merged to `main`. Phase 2 closed on 2026-04-30 with 57 files changed, 4 593
insertions, and 85 deletions net across the spec window.

The test suite ends at **93.65 % coverage** (345 passed, 2 skipped pending a
live Ollama instance), comfortably above the 90 % gate. Nine syrupy snapshots
covering generator output shapes all pass.

## Decisions that changed the spec or are load-bearing for phase 3

**PersonalizationProfile is a Pydantic `BaseModel`, not a `TypedDict`.**
`docs/02-data-model.md` suggested `TypedDict`, but a `TypedDict` cannot enforce
the non-empty `justification` invariant on `ReplacementRecord` at construction
time. The Pydantic `field_validator` catches violations before persistence.
Phase 3 generators that produce `PersonalizationProfile` instances must use the
Pydantic constructor path, not dict literals (see ADR-0009).

**`AssessmentItem.concept_id` is a denormalised field, not a join.**
The gap detector queries `concept_id` on every quiz submission, so an O(1)
column lookup outweighs the minor schema redundancy. Phase 3 must continue
populating `concept_id` at generation time — it is not backfill-able via span
join (ADR-0010).

**Validator protocol uses structural typing with collect-all semantics.**
`Validator[T]` is a `Protocol`; no ABC inheritance is required. `run_validators`
collects all failures before raising, so generators see the complete failure set
in one call. MCQGenerator deliberately does _not_ call `run_validators` — it
iterates validators manually and discards failing items rather than aborting. The
distinction (discard vs. raise) is load-bearing: phase 3 generators that produce
batches should match MCQGenerator's pattern; generators that produce a single
result should raise (as MnemonicGenerator does) (ADR-0011).

**ExampleReplacer discards faithfulness failures silently; MnemonicGenerator
raises.** A mnemonic has no fallback — discarding silently would return nothing.
An example replacement batch can survive partial failure. Phase 3 generators
should adopt the same asymmetry based on whether a partial result is meaningful.

**`GlowsGrows` is a frozen dataclass, not a Pydantic model.** This keeps
`dataclasses.asdict()` available for snapshot tests and avoids pulling Pydantic
into the quiz serialisation path. Phase 3 code that needs to serialise
`GlowsGrows` should use `dataclasses.asdict()`, not `.model_dump()`.

**Gap detector is stateless and dao-parameterised.** `GapDetector.next_concept`
takes a `dao` parameter at call time, not at `__init__`. One detector instance
can serve multiple DAO instances. Phase 3 endpoints that need personalised
sequencing should reuse this pattern rather than injecting state into the
detector.

**Grade-level validation lives on the request model, not the domain model.**
`CreateProfileRequest` validates `grade_level`; FastAPI converts that to a 422.
Duplicating the validator in `LearnerProfile` itself is unnecessary and was
explicitly rejected. Phase 3 endpoints that accept profile-linked data should
follow the same pattern.

## What was harder than expected

**T10 — section-quality validators, especially `EmphasisValidator`.**
The first cut of the emphasis check fired false positives on small sections where
a zero-prerequisite concept had simply not yet accumulated items. The final rule
requires _both_ conditions simultaneously: a high-prerequisite concept with zero
items _and_ a zero-prerequisite concept with two or more items. Single-condition
tests would incorrectly reject valid small sections. The `bloom_level=None`
sentinel for untagged items (pre-T8 paths) also required an explicit decision:
treat `None` as `"remember"` so untagged items never silently satisfy the active
learning gate.

**T7 — defining "personalizable" conservatively.** The prompt boundary — what
counts as an analogy or scenario versus core content — was the hardest design
decision in the phase. The final definition (explicit analogies, illustrative
scenarios, and flavor text; definitions, equations, named theorems, and formal
proofs are never rewritten) was settled during implementation and recorded in the
prompt module's docstring. Faithfulness failures were discarded rather than
raised, which required a deliberate divergence from T11's raise-on-failure
pattern.

**T13 — non-MCQ items and the `suggested_next_concept_id` gap.** Items without
a `correct_answer` (short-answer, open-ended) cannot be machine-graded. Rather
than returning a 5xx, the endpoint returns `correct=False` and
`rationale="Manual evaluation required"`. This is semantically correct but
required explicitly deciding that the caller bears responsibility for filtering
non-gradable items. Separately, `suggested_next_concept_id` in `AttemptFeedback`
is always `None` because `quiz_id` tracking is not yet wired; that gap was
flagged as an out-of-spec discovery rather than held as a blocker.

## What was easier than expected

**The validator framework generalised without rework.** The Protocol-based
`Validator[T]` seam established in T3 absorbed T4, T6, and T10 without changes
to the base. Each new validator was independently testable and required no
inheritance ceremony. The collect-all semantics in `run_validators` meant the
generator layer never had to loop; one call returned all failures.

**Snapshot testing for generators.** The syrupy pattern established during phase
1 propagated cleanly through T5, T7, T9, and T11. Mocking `ModelClient.complete`
with a `side_effect` list was sufficient to cover multi-call generators without
touching the real model. Nine snapshots covering generator output shapes give a
cheap regression net for prompt changes.

**The TDD rhythm held for every task.** Failing tests preceded implementation in
every task. No fix-pass commits were required for ruff or mypy after the initial
implementation (unlike T5 and T14 in phase 1, which needed separate fix
commits). The `asyncio_mode = "auto"` setting from phase 1 continued to mean
every async test just worked.

**Schema carry-overs resolved cleanly.** T0c-r1 through T0c-r3 resolved the
phase 1 `dict[str, Any]` placeholder and added `correct_answer`, `bloom_level`,
and `prerequisites` ordering before any feature task opened. No feature task had
to paper over a missing field.

## Carry-overs into phase 3

**`suggested_next_concept_id` is always `None`.**
`POST /recommendations/next` returns a next concept correctly, but
`AttemptFeedback.suggested_next_concept_id` in the attempts response is always
`None` because `quiz_id`-to-`SectionQuiz` tracking is not implemented. Glows/
Grows integration in the attempts response requires that linkage.

**Generator output is never persisted.** `ReLeveler`, `ExampleReplacer`, and
`MnemonicGenerator` all return `(text, profile)` or records; they do not write
`DerivedAsset` rows or files. Phase 3 must wire generators through the Arq
worker and the filesystem adapter (`lyw_core.storage.fs`) before personalized
content is durable. The layering is correct — the generator/persistence split is
intentional — but the persistence half is fully deferred.

**No `POST /lessons/{id}/generate` route yet.** The Arq worker has an ingest
job from phase 1 but no personalization job. Phase 3 must add a generation
job and the corresponding API trigger before end-to-end personalization is
possible.
