# Phase 3 — Modality generators

## Goal

Add modality generators on top of the personalized lesson graph. Each
modality is a separate generator with a modality-specific validator.
All generators consume the canonical lesson graph and produce
`DerivedAsset` instances with full provenance.

## Order of work

Strict order. Do not jump ahead.

1. Mind maps (Mermaid output).
2. Timelines (Mermaid output for chronological content).
3. Slides (text content and speaker notes; no narration).

Mind maps and timelines come first because they are the simplest
structurally — Mermaid source generated from the lesson graph.
Slides require more layout decisions and structured content per
slide, so they ship last.

Illustration generation is **not** part of phase 3. Reliable
educational image generation requires either a fine-tuned domain
model with a dataset reviewed for educational accuracy, or a
retrieval-only path that pulls verified figures from the source. Both
are out of scope until a later phase. Diagram-as-code (Mermaid) covers
the structural visual cases that phase 3 needs.

## Deliverables

- [ ] Mind-map generator producing Mermaid diagrams from the concept
      graph. Persists output as `DerivedAsset` with `kind="mind_map"`.
- [ ] Timeline generator for chronological content. The lesson graph
      must record temporal ordering for this to be meaningful. Persists
      output as `DerivedAsset` with `kind="timeline"`.
- [ ] Slide generator producing structured slide decks with speaker
      notes. Source spans on every slide. Persists output as
      `DerivedAsset` with `kind="slides"`.
- [ ] Modality-specific validators that gate persistence, implemented
      as `Validator[T]` Protocols (ADR-0011). Single-output generators
      (mind map, timeline) raise `ValidationError` on failure;
      slide generators may discard individual failing slides.
- [ ] Wire the three new modality generators into the
      `personalize_concept` Arq job. `POST /lessons/{id}/generate` and
      `GET /lessons/{id}/generate/{job_id}` are already implemented
      (PR #47); phase 3 extends the job to dispatch `mind_map`,
      `timeline`, and `slides` generator kinds.
- [ ] Asset retrieval by ID via the existing `get_derived_asset` DAO.

## Out of scope

- Audio of any kind. No TTS, no narration, no audio lessons.
- Illustration / image generation.
- Real-time / streaming generation. All modality generation is async.
- Cross-modality coherence beyond what the shared lesson graph
  provides.
- Multi-language support. Phase 3 is English-only.

## Acceptance criteria

- Each modality generator records `based_on_concepts` on the produced
  `DerivedAsset`. Source-span traceability is at per-component granularity —
  per slide for `slides`, per node for `mind_map` and `timeline` — and is
  satisfied via the spans on referenced `ConceptNode` instances; the
  `DerivedAsset` envelope does not duplicate those spans. The
  `personalization_profile` field must be a typed `PersonalizationProfile`
  Pydantic model instance (ADR-0009); raw dicts are a type error.
- Validators reject assets that fail the pedagogy rubrics from
  `docs/02-data-model.md`. Validators are implemented as
  `Validator[T]` Protocols using the framework in
  `lyw_core/validators/base.py` (ADR-0011).
- Asynchronous generation does not block interactive paths (quiz
  feedback, guided hints).
- Phase 3 tasks must maintain the 93 % coverage gate (`fail_under =
  93` in `pyproject.toml`, raised in PR #45).

## Implementation notes

- Mermaid is straightforward to generate; the trick is pruning the
  concept graph to a useful size for any one diagram. Define a
  per-diagram concept budget (e.g., 12-20 nodes) and prune by
  prerequisite distance from a focal concept.
- Timelines require chronological metadata on `ConceptNode`. If a
  source has no temporal structure, the timeline generator skips it.
- Slide generation needs an explicit outline step. Generate the
  outline first (titles, key points per slide, source spans), then
  flesh out each slide. This makes errors recoverable.
- Each generator has its own validator. Validators run before the
  asset is persisted. A failed validation rejects the asset; it does
  not patch it. Generation may be retried with adjusted prompts.
- All generators are pure functions returning text or structured data.
  Persistence uses two complementary stores (ADR-0013): file content is
  written to content-addressed storage via `DataDir.write_asset(data,
  suffix=...)` (SHA-256 over bytes — identical content deduplicates to the
  same file); metadata is keyed in the `derived_assets` SQLite table by the
  lookup tuple `(lesson_id, concept_id, kind, profile_id)`. The
  `personalize_concept` Arq job orchestrates both writes via
  `save_derived_asset`; generators must not call it directly.
- **Two `DerivedAsset` types**: `lesson_graph.models.DerivedAsset` (Pydantic)
  is the generator-output domain model with `based_on_concepts` and a rich
  `personalization_profile` object. `lyw_core.db.dao.DerivedAsset` (plain
  dataclass) is the persistence record with scalar `concept_id`, `profile_id`,
  and `file_path`. Generators construct the Pydantic model; the Arq job
  derives the DAO record from it before calling `save_derived_asset`.
- Lesson-level generator kinds (`mind_map`, `timeline`) have no single
  `concept_id`; use the sentinel constant `LESSON_SCOPED_CONCEPT_ID`
  (`"__lesson__"`) from `src/lyw_core/db/dao.py` for both the job parameter
  and the DAO record.
- Mind-map and timeline generators produce a single output and must
  call `run_validators` (collect-all, raises `ValidationError`).
  The slide generator may produce per-slide output and should iterate
  validators manually, discarding failing slides rather than aborting,
  matching the `MCQGenerator` pattern (ADR-0011, phase-2 retrospective).
- `PersonalizationProfile` instances must be constructed via the
  Pydantic constructor, not from dict literals (ADR-0009). `GlowsGrows`
  instances (if used in feedback paths) should be serialised with
  `dataclasses.asdict()`, not `.model_dump()`.
- The carry-over from phase 2 — `quiz_id` tracking and Glows/Grows
  in `AttemptFeedback` — is not required by phase 3 modality
  deliverables but must be resolved if phase 3 adds any endpoint
  that surfaces Glows/Grows data. If deferred, record it explicitly
  as accepted technical debt.
