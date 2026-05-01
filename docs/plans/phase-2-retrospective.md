# Phase 2 Retrospective

> ⚠️ **This document has been superseded.** The Phase 2 scope was cut per [ADR-0016](../adr/0016-scope-cut-phase-2-3.md). Only re-leveling and interest-based example replacement remain; all other deliverables documented here have been deleted. Refer to the ADR for the scope cut rationale.

## What shipped

All nineteen spec deliverables from `specs/phase-2-personalization.md` landed, plus
three out-of-spec items that resolved carry-overs before the phase formally closed.
The tracker is fully checked off: three carry-over schema tasks (T0c-r1 through
T0c-r3), two profile tasks (T1, T2), the validator framework (T3), four
validators (T4, T6, T10, and the faithfulness sub-check inside T5), three
generators (T5, T7, T11), the section quiz with Glows/Grows feedback (T8, T9),
and the gap detection and API endpoints (T12, T13). Sixteen PRs (#21–#35) were
merged to `main` against the spec window.

After the tracker closed, three follow-on PRs shipped before phase 2 was
declared done. PR #44 wired `GapDetector.next_concept` into
`POST /v1/attempts` so that `AttemptFeedback.suggested_next_concept_id` is
populated from the gap detector instead of always returning `None`. PR #46
added the `derived_assets` SQLite table, a `save_derived_asset` /
`get_derived_asset` DAO pair, a `personalize_concept` Arq job that runs any of
the three generators and writes output to content-addressed storage, and
ADR-0013. PR #47 added `POST /lessons/{lesson_id}/generate` (202 enqueues the
Arq job) and `GET /lessons/{lesson_id}/generate/{job_id}` (polling endpoint).
These three PRs resolved all four carry-overs from the initial retrospective
draft with the exception of `quiz_id` tracking, which remains open into phase 3.

The test suite finished at 93.65 % coverage (345 passed, 2 skipped pending a
live Ollama instance), well above the 90 % gate. Nine syrupy snapshots covering
generator output shapes all pass.

## Decisions that changed the spec or are load-bearing for phase 3

**`PersonalizationProfile` is a Pydantic `BaseModel`, not a `TypedDict` (T0c-r1).**
`docs/02-data-model.md` suggested `TypedDict`, but a `TypedDict` cannot enforce
the non-empty `justification` invariant on `ReplacementRecord` at construction
time. The Pydantic `field_validator` catches violations before persistence. Phase 3
generators that produce `PersonalizationProfile` instances must use the Pydantic
constructor path, not dict literals (ADR-0009).

**`AssessmentItem.concept_id` is a denormalised field, not a join (T0c-r2).**
The gap detector queries `concept_id` on every quiz submission, so an O(1) column
lookup outweighs the minor schema redundancy. Phase 3 must continue populating
`concept_id` at generation time — it is not backfill-able via span join
(ADR-0010).

**Validator protocol uses structural typing with collect-all semantics (T3).**
`Validator[T]` is a `Protocol`; no ABC inheritance is required. `run_validators`
collects all failures before raising, so generators see the complete failure set
in one call. `MCQGenerator` deliberately does not call `run_validators` — it
iterates validators manually and discards failing items rather than aborting. The
distinction (discard vs. raise) is load-bearing: phase 3 generators that produce
batches should match `MCQGenerator`'s pattern; generators that produce a single
result should raise (as `MnemonicGenerator` does) (ADR-0011).

**`ExampleReplacer` discards faithfulness failures silently; `MnemonicGenerator`
raises (T7, T11).** A mnemonic has no fallback — discarding silently would return
nothing. An example replacement batch can survive partial failure. Phase 3
generators should adopt the same asymmetry based on whether a partial result is
meaningful. `original_span` for all replacements is always `concept.source_spans[0]`
because the model operates on text, not character offsets; this is the conservative
anchor that keeps all replacements traceable (T7 decision).

**`GlowsGrows` is a frozen dataclass, not a Pydantic model (T9).**
This keeps `dataclasses.asdict()` available for snapshot tests and avoids pulling
Pydantic into the quiz serialisation path. Phase 3 code that needs to serialise
`GlowsGrows` should use `dataclasses.asdict()`, not `.model_dump()`.

**Gap detector is stateless and dao-parameterised (T12).**
`GapDetector.next_concept` takes a `dao` parameter at call time, not at
`__init__`. One detector instance can serve multiple DAO instances. Phase 3
endpoints that need personalised sequencing should reuse this pattern.

**`POST /v1/attempts` populates `suggested_next_concept_id` via a
`get_lesson_id_by_concept_id` DAO method (PR #44).** The spec listed this as
deferred; it shipped as a follow-on before phase close. The DAO method resolves
concept to lesson so the gap detector can load the correct lesson graph per
request. This is the correct layering for phase 3.

**Generator persistence uses two complementary stores (PR #46, ADR-0013).**
The `personalize_concept` Arq job writes generator output bytes via
`DataDir.write_asset(data, suffix=...)` (SHA-256 content-addressed; identical
content deduplicates) and stores the resulting path on the DAO `DerivedAsset`
record. Metadata is queried via the `derived_assets` SQLite table keyed by
`(lesson_id, concept_id, kind, profile_id)`. Phase 3 modality generators must
follow the same two-store pattern.

**Non-MCQ items return `correct=False` with `rationale="Manual evaluation
required"` rather than 5xx (T13).** Items without `correct_answer` cannot be
machine-graded. The endpoint must remain safe for all item kinds; the caller
decides how to handle the manual-eval signal.

**Grade-level validation lives on the request model, not the domain model (T2).**
`CreateProfileRequest` validates `grade_level`; FastAPI converts that to a 422.
Duplicating the validator in `LearnerProfile` itself was explicitly rejected.
Phase 3 endpoints that accept profile-linked data should follow the same pattern.

## What was harder than expected

**T10 — section-quality validators, especially `EmphasisValidator`.**
The first cut of the emphasis check fired false positives on small sections where
a zero-prerequisite concept had simply not yet accumulated items. The final rule
requires both conditions simultaneously: a high-prerequisite concept with zero
items and a zero-prerequisite concept with two or more items. Single-condition
tests would incorrectly reject valid small sections. The `bloom_level=None`
sentinel for untagged items also required an explicit decision: treat `None` as
`"remember"` so untagged items never silently satisfy the active learning gate.

**T7 — defining "personalizable" conservatively.**
The prompt boundary — what counts as an analogy or scenario versus core content —
was the hardest design decision in the phase. The final definition (explicit
analogies, illustrative scenarios, and flavor text; definitions, equations, named
theorems, and formal proofs are never rewritten) was settled during implementation
and recorded in the prompt module's docstring. Faithfulness failures were discarded
rather than raised, which required a deliberate divergence from T11's
raise-on-failure pattern.

**T13 — non-MCQ items and the `suggested_next_concept_id` gap.**
Items without `correct_answer` cannot be machine-graded. The endpoint returns
`correct=False` and `rationale="Manual evaluation required"` for such items.
`suggested_next_concept_id` was initially always `None` because `quiz_id`
tracking was not wired; that required a follow-on PR (#44) to resolve, adding
the `get_lesson_id_by_concept_id` DAO method and wiring `GapDetector` into the
attempts handler.

**PR #46 — generator persistence required a rebase conflict fix after squash.**
The derived-assets PR was rebased after T8's DAO additions; a conflict in
`schema.sql` and `dao.py` required a fix commit before the coverage gate
passed. The content-addressed storage design (ADR-0013) added conceptual
surface area that extended the session past the estimated time.

## What was easier than expected

**The validator framework generalised without rework.**
The Protocol-based `Validator[T]` seam established in T3 absorbed T4, T6, and
T10 without changes to the base. Each new validator was independently testable
and required no inheritance ceremony. The collect-all semantics in `run_validators`
meant the generator layer never had to loop; one call returned all failures.

**Snapshot testing for generators.**
The syrupy pattern established during phase 1 propagated cleanly through T5, T7,
T9, and T11. Mocking `ModelClient.complete` with a `side_effect` list was
sufficient to cover multi-call generators without touching the real model. Nine
snapshots covering generator output shapes give a cheap regression net for prompt
changes.

**The TDD rhythm held for every task.**
Failing tests preceded implementation in every task. No fix-pass commits were
required for ruff or mypy after the initial implementation pass. The
`asyncio_mode = "auto"` setting from phase 1 continued to mean every async test
just worked.

**Schema carry-overs resolved cleanly.**
T0c-r1 through T0c-r3 resolved the phase 1 `dict[str, Any]` placeholder and
added `correct_answer`, `bloom_level`, and `prerequisites` ordering before any
feature task opened. No feature task had to paper over a missing field.

**The Arq job pattern reused phase 1's worker scaffolding directly.**
PR #46's `personalize_concept` job slotted into the existing
`WorkerSettings` without structural changes; the ingest job pattern from phase 1
was the right template.

## Carry-overs into phase 3

- **`quiz_id` tracking and Glows/Grows in `AttemptFeedback`** are implemented in
  phase 3 by T0c-r3 (quiz_id schema change + DAO + SectionQuizGenerator wiring)
  and T0c-r4 (Glows-Grows in `POST /v1/attempts` response). These are promoted
  from accepted technical debt to phase-3 deliverables per the spec carry-over
  allowance.

- **`MnemonicResult` Pydantic type gap** — closed by phase-3 T0c-r1 (`SCHEMA_CHANGE=1`).
  The `personalize_concept` Arq job already persists mnemonics via the DAO
  (`_VALID_KINDS` includes `"mnemonic"`, `save_derived_asset` is called). T0c-r1
  widened `lesson_graph.models.DerivedAsset.kind` to include `"mnemonic"` in the
  Pydantic Literal, eliminating the type inconsistency between the domain model
  and the DAO dataclass.

- **`POST /lessons/{lesson_id}/generate` only enqueues; it does not poll or
  stream.** The GET polling endpoint returns `pending`, `complete`, or
  `not_found` state but there is no push mechanism. If phase 3 modality
  generators need progress reporting, a WebSocket or SSE layer will be required.

- **Coverage gate raised to 93 % during housekeeping (PR #45).** The gate was
  90 % at phase start and is now 93 % (`fail_under = 93` in `pyproject.toml`).
  Phase 3 tasks that add low-coverage paths (integration stubs, new route
  skeletons) must account for this tighter gate from the first task.
