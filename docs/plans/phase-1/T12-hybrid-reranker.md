# T12 - Cross-Encoder Reranker and Hybrid Pipeline

## Status

- [ ] T12: Cross-encoder reranker and hybrid pipeline

## Goal

Combine BM25 and Qdrant candidates, then rerank with
`ms-marco-MiniLM-L-6-v2`. This is the full retrieval surface consumed
by the inspection and later orchestration paths.

## Files

- Create `src/lyw_core/retrieval/reranker.py`.
- Create `src/lyw_core/retrieval/hybrid.py`.
- Fan out to BM25 and dense retrievers.
- Deduplicate candidates before reranking.
- Create `tests/unit/test_retrieval_reranker.py`.
- Create `tests/unit/test_retrieval_hybrid.py`.

## Depends On

- T10 for BM25 retrieval.
- T11 for Qdrant retrieval.

## Acceptance

- `uv run pytest tests/unit/test_retrieval_reranker.py tests/unit/test_retrieval_hybrid.py`
  passes.
- Every top-k hit has a resolvable `SourceSpan`.
- Reranker scores are bounded and stable run-to-run.

## Out of Scope

- Learning-to-rank.
- Online feedback.
- Generator-specific retrieval policies.

## Risk Notes

- None recorded.
