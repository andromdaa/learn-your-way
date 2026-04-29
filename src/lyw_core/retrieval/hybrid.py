from __future__ import annotations

from lyw_core.retrieval.reranker import CrossEncoderReranker
from lyw_core.retrieval.types import RetrievalHit, Retriever


class HybridRetriever:
    def __init__(
        self,
        bm25: Retriever,
        dense: Retriever,
        reranker: CrossEncoderReranker,
        fetch_k: int = 20,
    ) -> None:
        self._bm25 = bm25
        self._dense = dense
        self._reranker = reranker
        self._fetch_k = fetch_k

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalHit]:
        bm25_hits = self._bm25.retrieve(query, top_k=self._fetch_k)
        dense_hits = self._dense.retrieve(query, top_k=self._fetch_k)
        seen: set[str] = set()
        candidates: list[RetrievalHit] = []
        for hit in bm25_hits + dense_hits:
            if hit.concept_id not in seen:
                seen.add(hit.concept_id)
                candidates.append(hit)
        return self._reranker.rerank(query, candidates, top_k=top_k)
