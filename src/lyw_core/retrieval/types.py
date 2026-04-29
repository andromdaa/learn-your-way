from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from lesson_graph.models import SourceSpan


class RetrievalHit(BaseModel):
    concept_id: str
    score: float
    source_span: SourceSpan
    text: str


@runtime_checkable
class Retriever(Protocol):
    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalHit]: ...
