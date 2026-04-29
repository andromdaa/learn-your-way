# Phase 1 — Ingest and ground

## Goal

Build the ingest-and-ground layer. Parse PDFs, produce a canonical
lesson graph with source-span fidelity, and expose an inspection
interface so the user can verify concept boundaries before any
generation runs.

This is the foundation. No phase-2 or phase-3 work begins until phase
1 ships and the user has signed off on a smoke-test parse.

## Deliverables

- [ ] PDF parser using Docling produces a `ParsedDocument` with page
      and character offsets.
- [ ] Chunker emits `ConceptNode` instances populated from the parsed
      document. Every node has at least one non-empty `SourceSpan`.
- [ ] Inspection CLI: `lyw inspect <pdf>` prints the extracted concept
      tree with span anchors, learning objectives, and prerequisites.
- [ ] Round-trip test: every character in every span resolves back to
      the corresponding source text.
- [ ] Hybrid retrieval: BM25 (Haystack `InMemoryBM25Retriever`) plus
      dense vectors (Qdrant) plus a cross-encoder reranker.
- [ ] SQLite schema for lesson metadata and source registry.
- [ ] Local data directory layout for source PDFs and derived assets.
- [ ] `POST /sources` and `GET /lessons/{id}` endpoints from
      `docs/04-api.md` are functional end-to-end.
- [ ] `src/lesson_graph/models.py` schema is implemented and tested.
- [ ] `docker-compose.yml` brings up Qdrant and Redis.

## Out of scope

- Personalization (phase 2).
- Any modality generation including immersive text rewrites (phase 3).
- Quiz or assessment generation (phase 2).
- Web UI beyond the inspection CLI.
- Image extraction for downstream illustration generation.

## Acceptance criteria

- The OpenStax sample chapter at
  `tests/fixtures/openstax_chapter.pdf` parses successfully.
- 100% of `ConceptNode.source_spans` resolve to valid character
  offsets.
- The inspection CLI output is reviewed by the user before phase 2
  work begins.
- All schema invariants from `docs/02-data-model.md` hold.
- Hybrid retrieval returns relevant chunks for a smoke-test query
  set.

## Implementation notes

- Use Docling's parsed output directly. Do not roll a PDF parser.
- Concept extraction is the hard part. Start with a section-boundary
  heuristic (heading detection plus length thresholds) and refine with
  a Gemma 4 prompt that proposes concept titles, learning objectives,
  and prerequisites. The model output must be validated against the
  schema before persistence.
- Inspection CLI output should be diffable. The user will want to
  compare runs.
- Index building runs as a post-parse Arq job. A single worker is fine
  for phase 1.
