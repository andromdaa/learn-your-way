# T10 - BM25 Retrieval Pipeline and Embedding Model ADR

## Status

- [ ] T10: BM25 retrieval pipeline and embedding model ADR

## Goal

Build the first retrieval modality: in-process, deterministic, and no
external service. It indexes `ConceptNode` source-span text behind a
typed `Retriever` protocol. Also write ADR-0007 so T11 has the
embedding model decision recorded before dense retrieval begins.

## Files

- Create `src/lyw_core/retrieval/__init__.py`.
- Create `src/lyw_core/retrieval/types.py` with `RetrievalHit` and a
  `Retriever` protocol.
- Create `src/lyw_core/retrieval/bm25.py`.
- Create `tests/unit/test_retrieval_bm25.py`.
- Create `docs/adr/0007-embedding-model.md` pinning
  `sentence-transformers/all-MiniLM-L6-v2`.
- Modify `pyproject.toml` to add `haystack-ai`.

## Depends On

- T7, because chunks are what get indexed.

## Acceptance

- Top-k results are stable across runs on the tiny fixture.
- Every `RetrievalHit.source_span` resolves through the round-trip
  verifier.
- `mypy` is strict-clean.
- ADR-0007 is committed.

## Out of Scope

- Dense retrieval.
- Reranking.
- Persistence; this is in-memory and rebuilds on process restart per
  ADR-0001.

## Risk Notes

- None recorded.
