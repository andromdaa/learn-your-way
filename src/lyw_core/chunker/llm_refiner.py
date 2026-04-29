"""LLM-based concept node refiner.

Takes heuristic ConceptNodes and enriches them by calling a ModelClient
with a structured extraction prompt. The model response is validated
against LLMRefinedPayload before any field on the node is mutated.
"""

import json

from pydantic import BaseModel, ValidationError

from lesson_graph.interfaces.model_client import ChatMessage, ModelClient
from lesson_graph.models import ConceptNode
from lyw_core.chunker.prompts.concept_extraction import SYSTEM, USER_TEMPLATE

MAX_INPUT_CHARS: int = 4000
_TRUNCATION_SENTINEL: str = " [TEXT TRUNCATED]"


class LLMRefinerError(Exception):
    """Raised when the model returns an unparseable or schema-invalid response."""


class LLMRefinedPayload(BaseModel):
    """Schema for the JSON the model must return."""

    title: str
    summary: str
    learning_objective: str
    prerequisites: list[str] = []


class LLMRefiner:
    """Refines heuristic ConceptNodes using a ModelClient.

    Each call to ``refine`` sends the node's content to the model,
    validates the response, and returns a new node with
    ``provenance="llm_refined"``. Source spans and node id are preserved.
    """

    def __init__(self, client: ModelClient) -> None:
        self._client = client

    async def refine(self, node: ConceptNode) -> ConceptNode:
        text = node.summary
        if len(text) > MAX_INPUT_CHARS:
            text = text[:MAX_INPUT_CHARS] + _TRUNCATION_SENTINEL

        messages = self._build_messages(node.title, text)
        raw = await self._client.complete(messages, temperature=0.0)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMRefinerError(f"Model returned invalid JSON: {exc}") from exc

        try:
            payload = LLMRefinedPayload.model_validate(data)
        except ValidationError as exc:
            raise LLMRefinerError(
                f"Model payload failed schema validation: {exc}"
            ) from exc

        return node.model_copy(
            update={
                "title": payload.title,
                "summary": payload.summary,
                "learning_objective": payload.learning_objective,
                "prerequisites": payload.prerequisites,
                "provenance": "llm_refined",
            }
        )

    def _build_messages(self, title: str, text: str) -> list[ChatMessage]:
        return [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": USER_TEMPLATE.format(title=title, text=text),
            },
        ]
