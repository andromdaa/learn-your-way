# Phase 3 Tracker — Modality Generators

Compact index for Phase 3 task work. Detailed task files live in
`docs/plans/phase-3/`. The source contract is
`specs/phase-3-modalities.md`.

## Status

Not started. Phase 2 acceptance criteria closed 2026-04-30; phase 3
opens now. Four T0c-r tasks address phase-2 carry-overs before any feature
task opens: T0c-r1 (mnemonic Literal), T0c-r2 (temporal_position schema),
T0c-r3 (quiz_id schema + DAO), T0c-r4 (Glows-Grows in /attempts).

Each T-task is intended to be one branch, one PR, one agent session,
around 400 LoC, at most six files touched, no later T-numbers as
prerequisites.

## Tasks

- [ ] [T0c-r1: Add "mnemonic" to DerivedAsset.kind Pydantic Literal (SCHEMA_CHANGE=1)](phase-3/T0c-r1-carryover-debt.md)
- [ ] [T0c-r2: temporal_position schema change on ConceptNode (ADR-0014)](phase-3/T0c-r2-temporal-position-schema.md)
- [ ] [T0c-r3: quiz_id schema change + DAO + SectionQuizGenerator wiring (ADR-0015)](phase-3/T0c-r3-quiz-id-schema.md)
- [ ] [T0c-r4: Glows-Grows in POST /v1/attempts response](phase-3/T0c-r4-glows-grows-attempts.md)
- [ ] [T1: Mind-map generator + validator (Mermaid, single-output, raises on failure)](phase-3/T1-mindmap-generator.md)
- [ ] [T2: Mind-map Arq integration (extend personalize_concept + generate endpoint)](phase-3/T2-mindmap-arq.md)
- [ ] [T3: Timeline generator + validator (Mermaid, temporal skip path, raises on failure)](phase-3/T3-timeline-generator.md)
- [ ] [T4: Timeline Arq integration (extend personalize_concept + generate endpoint)](phase-3/T4-timeline-arq.md)
- [ ] [T5: Slide generator + validator (per-slide discard, MCQGenerator pattern)](phase-3/T5-slide-generator.md)
- [ ] [T6: Slide Arq integration + asset retrieval endpoint](phase-3/T6-slide-arq-retrieval.md)

## Decisions Made

- **Q1 — Lesson-level `concept_id` sentinel**: use named constant
  `LESSON_SCOPED_CONCEPT_ID = "__lesson__"` in `src/lyw_core/db/dao.py`.
  Avoids a nullable-column migration; uniform `WHERE concept_id = ?` DAO
  queries. T2 and T4 both use this constant.
- **Q2 — Mnemonic Pydantic Literal**: add `"mnemonic"` to
  `lesson_graph.models.DerivedAsset.kind` Literal in T0c-r1 (`SCHEMA_CHANGE=1`).
  DAO persistence already works; this closes the type-alignment gap.
- **Q3 — `temporal_position` type**: `int | None` (default `None`). Integer
  ordering rank; `None` = unordered/not applicable. `int` admits negatives
  (BC dates) and arbitrary ranks. `float`/`str` deferred until needed.
- **Q4 — `DerivedAsset.source_spans`**: no new field on `DerivedAsset`.
  Source-span traceability is per-component (per slide / per node) via
  referenced `ConceptNode.source_spans`. Spec acceptance criterion reworded
  accordingly.
- **C1 — Hash-key claim corrected**: ADR-0013 hashes file content bytes only
  (SHA-256 via `DataDir.write_asset`). The `(lesson_id, concept_id, kind,
  profile_id)` tuple is the SQLite lookup key, not the file-path key. AGENTS.md
  and spec corrected.
- **C2 — Two `DerivedAsset` types documented**: Pydantic model =
  generator-output domain model; DAO dataclass = persistence record. Arq job
  is the bridge. No refactor; layering documented in AGENTS.md and spec.
- **C3 — ADR-0013 kind enumeration removed**: stale `"relevel"|"replace"|"mnemonic"`
  enumeration replaced with a reference to `DerivedAsset.kind` Literal.
- **Q5 — Glows-Grows in AttemptFeedback**: promoted from accepted technical
  debt to phase-3 deliverable. The spec carry-over note authorises this:
  "must be resolved if phase 3 adds any endpoint that surfaces Glows/Grows
  data." T0c-r3 adds the `quiz_id` schema foundation; T0c-r4 wires
  Glows-Grows into `POST /v1/attempts`.

## Open Questions

_(empty — all four open questions and three concerns resolved; record new
blockers or ambiguities here as they arise)_

## Out-of-Spec Discoveries

_(empty — record anything found during implementation that conflicts
with or extends `specs/phase-3-modalities.md`. Each entry must end
with either "reconciled in PR #N" or "deferred to phase 4".)_

## Spec Coverage

| `specs/phase-3-modalities.md` deliverable | Covered by |
| --- | --- |
| Mind-map generator producing Mermaid diagrams; persists as `DerivedAsset(kind="mind_map")` | T1, T2 |
| Timeline generator for chronological content; persists as `DerivedAsset(kind="timeline")` | T0c-r2 (schema), T3, T4 |
| Slide generator with speaker notes and source spans per slide; persists as `DerivedAsset(kind="slides")` | T5, T6 |
| Modality-specific validators as `Validator[T]` Protocols (ADR-0011); single-output raises, slides discard per-item | T1, T3, T5 |
| Wire three generators into `personalize_concept` Arq job; extend `POST /lessons/{id}/generate` | T2, T4, T6 |
| Asset retrieval by ID via existing `get_derived_asset` DAO | T6 |
| Carry-over: `quiz_id` tracking + Glows-Grows in `AttemptFeedback` (spec carry-over allowance) | T0c-r3, T0c-r4 |
