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
      graph.
- [ ] Timeline generator for chronological content. The lesson graph
      must record temporal ordering for this to be meaningful.
- [ ] Slide generator producing structured slide decks with speaker
      notes. Source spans on every slide.
- [ ] Modality-specific validators that gate persistence.
- [ ] `POST /lessons/{id}/generate` returns 202, runs the job via
      Arq, persists the asset.
- [ ] Asset retrieval by ID.

## Out of scope

- Audio of any kind. No TTS, no narration, no audio lessons.
- Illustration / image generation.
- Real-time / streaming generation. All modality generation is async.
- Cross-modality coherence beyond what the shared lesson graph
  provides.
- Multi-language support. Phase 3 is English-only.

## Acceptance criteria

- Each modality generator records `based_on_concepts` and source
  spans on the produced `DerivedAsset`.
- Validators reject assets that fail the pedagogy rubrics from
  `docs/02-data-model.md`.
- Asynchronous generation does not block interactive paths (quiz
  feedback, guided hints).

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
