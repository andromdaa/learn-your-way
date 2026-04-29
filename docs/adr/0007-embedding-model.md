# ADR-0007: Embedding Model — `sentence-transformers/all-MiniLM-L6-v2`

## Status

Accepted

## Context

T11 adds dense retrieval over Qdrant. Before that work begins, the embedding
model must be pinned so the index schema, vector dimensions, and downstream
retrieval assumptions are stable. The choice affects:

- **Vector dimension** — Qdrant collection schema is created with a fixed `size`;
  changing the model later requires re-creating the collection and re-indexing.
- **Throughput** — ingest runs synchronously in an Arq worker; the model must be
  fast enough to index a chapter-length PDF without a perceptible stall.
- **Licensing** — must be Apache-2.0 or MIT compatible for an open-source repo.

## Decision

Pin `sentence-transformers/all-MiniLM-L6-v2` as the embedding model for all
phases of this project.

Key properties:
- **Dimension**: 384
- **License**: Apache 2.0
- **Max input tokens**: 256 (sufficient for ConceptNode-sized chunks)
- **Inference**: CPU-friendly; quantised versions available for constrained
  hardware

## Alternatives considered

| Model | Dimension | Notes |
|---|---|---|
| `BAAI/bge-small-en-v1.5` | 384 | Marginally better MTEB scores but less community tooling; no clear win for educational retrieval |
| `text-embedding-3-small` (OpenAI) | 1536 | Requires OpenAI API key; breaks the fully-local constraint from ADR-0001 and ADR-0005 |
| `all-mpnet-base-v2` | 768 | 2× dimension cost with no meaningful quality gain for short educational passages |

## Consequences

- T11 creates the Qdrant collection with `size=384`.
- The `sentence-transformers` package is added as a runtime dependency in T11.
- Model weights are downloaded once by the Arq worker on first run and cached
  by the HuggingFace hub under the configured cache directory.
- Switching models requires a data migration: drop and recreate the Qdrant
  collection and re-run the ingest pipeline.
