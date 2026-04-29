# Phase 1 Tracker

Compact index for Phase 1 task work. Detailed task plans live in
`docs/plans/phase-1/`. The source contract remains
`specs/phase-1-ingest.md`.

## Status

Not started. T0a tooling and T0b scaffolding smoke test shipped on
main. Phase 1 task work begins at T0c.

Each T-task is intended to be one branch, one PR, one agent session,
around 400 LoC, no more than six files touched, and no later
T-numbers as prerequisites.

## Tasks

- [x] [T0c: Package skeleton and test directory restructure](phase-1/T0c-package-skeleton.md)
- [ ] [T1: Settings, logging, runtime dependency manifest](phase-1/T1-settings-logging.md)
- [ ] [T2: Filesystem adapter and data directory layout](phase-1/T2-filesystem-adapter.md)
- [ ] [T3: Docker compose for Qdrant and Redis](phase-1/T3-services-healthcheck.md)
- [ ] [T4: SQLite schema, migrations, and source/lesson DAO](phase-1/T4-sqlite-dao.md)
- [ ] [T5: Docling PDF parser to ParsedDocument](phase-1/T5-docling-parser.md)
- [ ] [T6: Round-trip span verifier](phase-1/T6-span-verifier.md)
- [ ] [T7: Heuristic chunker and ConceptNode provenance field](phase-1/T7-heuristic-chunker.md)
- [ ] [T8: OllamaModelClient implementing ModelClient](phase-1/T8-ollama-client.md)
- [ ] [T9: LLM-refined chunker](phase-1/T9-llm-refined-chunker.md)
- [ ] [T10: BM25 retrieval pipeline and embedding model ADR](phase-1/T10-bm25-retrieval.md)
- [ ] [T11: Qdrant dense retrieval](phase-1/T11-qdrant-retrieval.md)
- [ ] [T12: Cross-encoder reranker and hybrid pipeline](phase-1/T12-hybrid-reranker.md)
- [ ] [T13: Inspection CLI](phase-1/T13-inspection-cli.md)
- [ ] [T14: Arq worker scaffolding and ingest pipeline](phase-1/T14-arq-ingest-worker.md)
- [ ] [T15: FastAPI sources and lessons endpoints](phase-1/T15-fastapi-endpoints.md)

## Decisions Made

- 2026-04-29: T0c uses a placeholder `integration`-marked test until real
  integration tests arrive. Rationale: `pytest -m integration` must exit 0
  before any service-backed tests exist, and the placeholder keeps the marker
  path selectable without requiring Qdrant, Redis, or end-to-end fixtures.

## Open Questions

_(empty - record blockers and ambiguities here. Resolve to a decision
or escalate to a spec/ADR change.)_

## Out-of-Spec Discoveries

_(empty - record anything found during implementation that conflicts
with or extends `specs/phase-1-ingest.md`. Each entry must end with
either "reconciled in PR #N" or "deferred to phase 2".)_

## Spec Coverage

| `specs/phase-1-ingest.md` deliverable | Covered by |
| --- | --- |
| PDF parser using Docling produces a `ParsedDocument` with page and character offsets. | T5 |
| Chunker emits `ConceptNode` instances with at least one non-empty `SourceSpan`. | T7, T9 |
| Inspection CLI prints concept tree with span anchors, learning objectives, and prerequisites. | T13 |
| Round-trip test: every character in every span resolves back to source text. | T6, exercised in T7, T9, T15 |
| Hybrid retrieval: BM25, dense vectors, and cross-encoder reranker. | T10, T11, T12 |
| SQLite schema for lesson metadata and source registry. | T4 |
| Local data directory layout for source PDFs and derived assets. | T2 |
| `POST /sources` and `GET /lessons/{id}` endpoints functional end-to-end. | T14, T15 |
| `src/lesson_graph/models.py` schema implemented and tested. | Shipped in T0; provenance field in T7 |
| `docker-compose.yml` brings up Qdrant and Redis. | T3 |
| `OllamaModelClient` implementing `ModelClient` protocol. | T8 |

## Architectural Artifacts

| Artifact | Task |
| --- | --- |
| ADR-0006: `lyw_core` sibling package | T0c |
| ADR-0007: embedding model (`all-MiniLM-L6-v2`) | T10 |
| ADR-0008: `ConceptNode.provenance` field | T7 |
| `tests/` reshaped into `unit/`, `integration/`, `fixtures/` | T0c |
| `integration` pytest marker | T0c |
