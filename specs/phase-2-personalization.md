# Phase 2 — Personalization and assessment

> **Status: superseded by [ADR-0016](../docs/adr/0016-phase-2-3-scope-reduction.md)
> (2026-05-01).** The deliverables marked dropped below are no longer in
> scope; the kept ones are the project's current focus. This file is
> retained as a historical reference.
>
> **Kept:** learner profile + `POST /profiles`, re-leveling, interest-based
> example replacement, `PersonalizationProfile`, `ReplacementRecord`.
>
> **Dropped:** embedded MCQs, section quizzes, glows/grows, mnemonics,
> quiz signal capture, gap detector, `POST /attempts`,
> `POST /recommendations/next`, `AssessmentItem.concept_id` schema change.

## Goal

Implement text personalization and assessment on top of the canonical
lesson graph from phase 1. Phase 3 modality generators consume the
output of this phase.

## Constraints from phase 1

These decisions were locked in phase 1 and shape the implementation
here:

- **`ConceptNode.provenance`** is `Literal["heuristic", "llm_refined"]`
  (ADR-0008). Phase 2 does not add a `"personalized"` value. Source
  `ConceptNode` instances are immutable after the ingest pipeline.
  Personalized content is stored as a `DerivedAsset`
  (kind=`"immersive_text"`), never as a mutated node.

- **Chunker granularity**: The heuristic chunker (T7) splits at
  heading boundaries with a `max_chars` cap. Concept nodes are
  section-sized, not paragraph-sized. Quiz items must cite spans that
  are strict subsets of at least one `ConceptNode.source_spans` entry;
  the generator prompt must enforce this so that gap detection is
  unambiguous.

- **SQLite `source_spans` table**: Concept-to-span relationships are
  stored relationally (T4 decision). The gap detector queries this
  table directly for concept lookup — not the hybrid retrieval
  pipeline, which is for user-facing search.

- **BM25 indexes one document per `ConceptNode`** (T10 decision).
  This is fine for retrieval but means the retrieval pipeline is not
  a substitute for the relational span lookup that gap detection
  needs.

## Deliverables

- [ ] Learner profile data model and `POST /profiles` endpoint.
- [ ] Re-leveling: rewrite text to a target readability that matches
      the learner's grade level. Every change diffable against source.
- [ ] Interest-based example replacement: replace clearly
      "personalizable" examples (analogies, sample problems) with
      examples tied to the learner's stated interests. Never invent
      content not anchored to a `SourceSpan`.
- [ ] ~~Embedded multiple-choice questions tied to learning objectives,
      with rationale and source citation.~~ **DROPPED — ADR-0016.**
- [ ] ~~Section-level quizzes (5–10 items per section) with "Glows" and
      "Grows" feedback.~~ **DROPPED — ADR-0016.**
- [ ] ~~Mnemonic memory aids for high-priority concepts.~~ **DROPPED — ADR-0016.**
- [ ] ~~Quiz signal capture and the gap detector that selects next-step
      concepts to revisit.~~ **DROPPED — ADR-0016.**
- [ ] ~~`POST /attempts` and `POST /recommendations/next` endpoints
      from `docs/04-api.md`.~~ **DROPPED — ADR-0016.**
- [ ] ~~**Schema change (SCHEMA_CHANGE=1 required)**: Add
      `concept_id: str` to `AssessmentItem` so the gap detector can
      map a failed quiz item directly to its parent concept. Requires
      updated tests in `tests/test_lesson_graph.py` and an ADR if
      semantically significant.~~ **DROPPED — ADR-0016 (`AssessmentItem`
      is being removed).**
- [ ] **Schema change (SCHEMA_CHANGE=1 required)**: Replace
      `DerivedAsset.personalization_profile: dict[str, Any]` with a
      typed `PersonalizationProfile` model. This model must include a
      `replacements: list[ReplacementRecord]` field where each
      `ReplacementRecord` carries the original `SourceSpan`, the
      replacement text, and a justification string. Requires updated
      tests and an ADR.

## Out of scope

- Any modality beyond immersive text — slides, mind maps, and
  timelines belong to phase 3.
- Illustration generation.
- Sequencing models or contextual-bandit personalization. Phase 2 is
  explicit-profile plus quiz feedback only.

## Acceptance criteria

- Personalization output is diffable against source. Every replacement
  in `PersonalizationProfile.replacements` carries the original
  `SourceSpan`, the replacement text, and a non-empty justification.
- A schema-conforming `PersonalizationProfile` (replacing
  `dict[str, Any]`) is implemented in `src/lesson_graph/models.py`,
  documented in `docs/02-data-model.md`, and covered by tests.
- `AssessmentItem.concept_id` is present and non-empty on every
  persisted item. The field references a `ConceptNode.id` in the
  same lesson graph.
- Quiz items satisfy all `AssessmentItem` invariants from
  `docs/02-data-model.md`, including that every `source_span` cited
  by an item is a subset of the parent concept's span range.
- For a smoke-test learner profile, the gap detector recommends a
  concept whose `source_spans` cover the failed quiz item's span.
  The lookup path is: failed item → `concept_id` → concept's
  prerequisites → highest-priority unmastered prerequisite.
- Pedagogy rubrics from `docs/02-data-model.md` are encoded as
  validators that gate persistence of personalized text and quiz
  items.

## Implementation notes

- Re-leveling is a constrained generation task. The prompt must
  instruct the model to preserve facts, terminology, and structure;
  only sentence complexity and word choice may change.
- Example replacement is more delicate. Define what counts as a
  "personalizable" segment up front (analogies, illustrative
  scenarios, flavor text) and refuse to rewrite anything else. Each
  replacement becomes one `ReplacementRecord` in
  `PersonalizationProfile.replacements`.
- Quiz generation prompts must require the model to cite source
  spans and the parent `ConceptNode.id`. Discard items where the
  cited span does not fall within the parent concept's span range,
  or where `concept_id` does not resolve to a known concept.
- The gap detector in v1 is rule-based: the failed item's
  `concept_id` identifies the concept; the detector returns the
  highest-priority unmastered prerequisite from that concept's
  `prerequisites` list. No vector lookup needed. Sequencing models
  are out of scope.
- `PersonalizationProfile` replaces the `dict[str, Any]`
  placeholder. Design it as a Pydantic model (not a plain
  `TypedDict`) so validators can enforce the `ReplacementRecord`
  invariants before persistence.

## Pedagogy rubrics

Encoded as validators:

- Source faithfulness: no claim in personalized text or quiz item is
  unsupported by a `SourceSpan`.
- Coverage: section quizzes touch every learning objective in the
  section.
- Emphasis: section quizzes weight high-priority objectives more than
  low-priority ones.
- Adaptability: re-leveling actually moves the readability score
  toward the target grade.
- Active learning: each section produces at least one item that
  requires application or analysis, not pure recall.
- Clarity of learning intentions: every quiz item names the objective
  it assesses (via `concept_id` → `ConceptNode.learning_objective`).
