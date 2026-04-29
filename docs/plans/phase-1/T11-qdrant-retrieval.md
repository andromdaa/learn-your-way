# T11 - Qdrant Dense Retrieval

## Status

- [ ] T11: Qdrant dense retrieval

## Goal

Implement dense retrieval against Qdrant using the embedding model
pinned in ADR-0007: `all-MiniLM-L6-v2`. The implementation stays
behind the `Retriever` protocol from T10 and indexes chunk text into
a per-lesson Qdrant collection.

## Files

- Create `src/lyw_core/retrieval/embedding.py`.
- Wrap `sentence-transformers/all-MiniLM-L6-v2`.
- Create `src/lyw_core/retrieval/qdrant.py` with indexer and
  retriever components.
- Create `tests/integration/test_retrieval_qdrant.py` with
  `@pytest.mark.integration`.
- Use testcontainers Qdrant; skip cleanly without Docker.

## Depends On

- T3 for the Qdrant service.
- T10 for the `Retriever` protocol and ADR-0007.

## Acceptance

- `uv run pytest -m integration tests/integration/test_retrieval_qdrant.py`
  passes against testcontainers Qdrant.
- Collection names are namespaced per lesson id.
- `uv run mypy` is strict-clean.

## Out of Scope

- Hybrid scoring.
- Multi-source collections.
- Embedding cache.
- GPU acceleration.

## Risk Notes

- `sentence-transformers` installs torch. Confirm the full install
  works in CI before merging T11.
