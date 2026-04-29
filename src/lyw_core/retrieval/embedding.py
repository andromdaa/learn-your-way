from typing import Any, cast

from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
VECTOR_DIM = 384


class EmbeddingModel:
    def __init__(self) -> None:
        self._model: Any = SentenceTransformer(MODEL_NAME)

    def encode(self, texts: list[str]) -> list[list[float]]:
        vecs: Any = self._model.encode(texts, convert_to_numpy=True)
        return cast(list[list[float]], vecs.tolist())
