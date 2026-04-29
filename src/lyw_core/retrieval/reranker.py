from __future__ import annotations

from typing import Any

from sentence_transformers import CrossEncoder

from lyw_core.retrieval.types import RetrievalHit

CROSS_ENCODER_MODEL = "ms-marco-MiniLM-L-6-v2"


class CrossEncoderReranker:
    def __init__(self, model: Any = None) -> None:
        self._model: Any = (
            model if model is not None else CrossEncoder(CROSS_ENCODER_MODEL)
        )

    def rerank(
        self, query: str, hits: list[RetrievalHit], top_k: int
    ) -> list[RetrievalHit]:
        if not hits:
            return []
        pairs = [[query, h.text] for h in hits]
        scores: Any = self._model.predict(pairs)
        scored = sorted(
            zip(hits, scores, strict=False), key=lambda x: float(x[1]), reverse=True
        )
        return [
            RetrievalHit(
                concept_id=h.concept_id,
                score=float(s),
                source_span=h.source_span,
                text=h.text,
            )
            for h, s in scored[:top_k]
        ]
