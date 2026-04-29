from typing import Any

from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
from haystack.dataclasses import Document
from haystack.document_stores.in_memory import InMemoryDocumentStore

from lesson_graph.models import ConceptNode, SourceSpan
from lyw_core.retrieval.types import RetrievalHit


class BM25Retriever:
    """In-process BM25 retrieval over indexed ConceptNodes.

    Stateless across restarts; call index() once per process before querying.
    """

    def __init__(self) -> None:
        self._store: InMemoryDocumentStore = InMemoryDocumentStore()

    def index(self, concepts: list[ConceptNode]) -> None:
        """Build the BM25 index from a list of ConceptNodes.

        One Haystack Document is created per concept, using its first
        source_span as the canonical provenance anchor.
        """
        docs: list[Document] = []
        for concept in concepts:
            text = f"{concept.title} {concept.summary} {concept.learning_objective}"
            span = concept.source_spans[0]
            meta: dict[str, Any] = {
                "concept_id": concept.id,
                "source_span": span.model_dump(),
            }
            docs.append(Document(content=text, meta=meta))
        self._store.write_documents(docs)

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalHit]:
        retriever = InMemoryBM25Retriever(document_store=self._store)
        result = retriever.run(query=query, top_k=top_k)
        hits: list[RetrievalHit] = []
        for doc in result["documents"]:
            if doc.score is None or doc.content is None:
                continue
            hits.append(
                RetrievalHit(
                    concept_id=str(doc.meta["concept_id"]),
                    score=doc.score,
                    source_span=SourceSpan(**doc.meta["source_span"]),
                    text=doc.content,
                )
            )
        return hits
