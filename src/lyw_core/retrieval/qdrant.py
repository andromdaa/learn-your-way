from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from lesson_graph.models import ConceptNode, SourceSpan
from lyw_core.retrieval.embedding import VECTOR_DIM, EmbeddingModel
from lyw_core.retrieval.types import RetrievalHit


def _collection_name(lesson_id: str) -> str:
    return f"lesson_{lesson_id}"


class QdrantIndexer:
    def __init__(self, client: QdrantClient, embedding: EmbeddingModel) -> None:
        self._client = client
        self._embedding = embedding

    def index(self, lesson_id: str, concepts: list[ConceptNode]) -> None:
        name = _collection_name(lesson_id)
        if self._client.collection_exists(name):
            self._client.delete_collection(name)
        self._client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )
        texts = [f"{c.title} {c.summary} {c.learning_objective}" for c in concepts]
        vectors = self._embedding.encode(texts)
        points = [
            PointStruct(
                id=i,
                vector=vec,
                payload={
                    "concept_id": concepts[i].id,
                    "source_span": concepts[i].source_spans[0].model_dump(),
                    "text": texts[i],
                },
            )
            for i, vec in enumerate(vectors)
        ]
        self._client.upsert(collection_name=name, points=points)


class QdrantRetriever:
    def __init__(
        self, client: QdrantClient, embedding: EmbeddingModel, lesson_id: str
    ) -> None:
        self._client = client
        self._embedding = embedding
        self._lesson_id = lesson_id

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalHit]:
        vector = self._embedding.encode([query])[0]
        response = self._client.query_points(
            collection_name=_collection_name(self._lesson_id),
            query=vector,
            limit=top_k,
        )
        hits: list[RetrievalHit] = []
        for result in response.points:
            payload = result.payload or {}
            hits.append(
                RetrievalHit(
                    concept_id=str(payload["concept_id"]),
                    score=result.score,
                    source_span=SourceSpan(**payload["source_span"]),
                    text=str(payload["text"]),
                )
            )
        return hits
