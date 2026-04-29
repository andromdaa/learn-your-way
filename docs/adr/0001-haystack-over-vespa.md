# ADR-0001: Haystack with Qdrant + InMemoryBM25 over Vespa or OpenSearch

## Status

Accepted.

## Context

The system needs hybrid retrieval: lexical (BM25) plus dense vectors
plus a reranker. The retrieval layer serves both interactive queries
(quiz feedback, guided hints) and the generation pipelines (concept
extraction, modality generators).

The deployment target is a single self-hosted machine with one user.

## Decision

Use Haystack as the orchestration layer, with:

- BM25 via Haystack's `InMemoryBM25Retriever`.
- Dense vectors via Qdrant, running as a Docker container.
- Cross-encoder reranking via sentence-transformers
  (`ms-marco-MiniLM-L-6-v2`), loaded into the app process.

## Consequences

Positive:

- Single dependency for retrieval orchestration. Haystack already
  knows how to combine BM25 + dense + reranker.
- One additional service to run (Qdrant). Redis for Arq is the only
  other moving piece.
- BM25 in-process avoids running a separate Lucene-based service
  (OpenSearch) for what is, at this scale, a few thousand chunks.

Negative:

- In-memory BM25 rebuilds on process restart. Acceptable at
  single-user scale; would not scale to multi-tenant.
- Tied to Haystack's pipeline abstractions. Migration to a different
  orchestrator would require rewiring the generation pipelines.

## Alternatives considered

**Vespa.** Production-grade serving for search and online
recommendation/personalization. Right call when ranking is the
core value and concurrency is high. We have neither concurrency nor
online ranking concerns; Vespa's operational footprint isn't
justified.

**OpenSearch + Qdrant + custom orchestration.** Two heavy services
plus glue code we'd have to write and maintain. Haystack already
provides the glue with one service deletion (OpenSearch).

**Pyserini.** Strong for offline IR experiments. Not designed as a
production retrieval layer, and pulling Lucene into the Python
runtime adds JVM and packaging complexity for no win at this scale.
