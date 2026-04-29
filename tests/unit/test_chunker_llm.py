"""Unit tests for LLMRefiner.

All model calls are intercepted by StubModelClient — no running Ollama required.
"""

import json

import pytest

from lesson_graph.interfaces.model_client import ChatMessage, ModelClient
from lesson_graph.models import ConceptNode, SourceSpan
from lyw_core.chunker.llm_refiner import LLMRefiner, LLMRefinerError

# ---------------------------------------------------------------------------
# Stub client
# ---------------------------------------------------------------------------


class StubModelClient:
    """ModelClient stub that returns a canned string response."""

    def __init__(self, response: str) -> None:
        self._response = response
        self.calls: list[list[ChatMessage]] = []

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> str:
        self.calls.append(messages)
        return self._response


def _stub_satisfies_protocol(client: StubModelClient) -> ModelClient:
    return client  # static check: satisfies ModelClient protocol


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_node(summary: str = "Photosynthesis converts light to sugar.") -> ConceptNode:
    return ConceptNode(
        id="abc123",
        title="Photosynthesis",
        summary=summary,
        learning_objective="Understand photosynthesis",
        source_spans=[
            SourceSpan(
                doc_id="doc-1",
                page_start=1,
                page_end=1,
                char_start=0,
                char_end=40,
            )
        ],
        prerequisites=[],
        provenance="heuristic",
    )


def _make_valid_response(
    title: str = "Photosynthesis",
    summary: str = "Plants use sunlight, water, and CO2 to produce glucose.",
    learning_objective: str = "Explain how plants convert light energy to chemical energy.",
    prerequisites: list[str] | None = None,
) -> str:
    return json.dumps(
        {
            "title": title,
            "summary": summary,
            "learning_objective": learning_objective,
            "prerequisites": prerequisites if prerequisites is not None else [],
        }
    )


# ---------------------------------------------------------------------------
# Well-formed payload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_well_formed_payload_refines_node() -> None:
    response = _make_valid_response(
        title="Photosynthesis Refined",
        summary="Plants convert light to glucose via chlorophyll.",
        learning_objective="Describe the light-dependent reactions.",
        prerequisites=["Cell biology basics"],
    )
    client = StubModelClient(response)
    refiner = LLMRefiner(client)

    result = await refiner.refine(_make_node())

    assert result.provenance == "llm_refined"
    assert result.title == "Photosynthesis Refined"
    assert result.summary == "Plants convert light to glucose via chlorophyll."
    assert result.learning_objective == "Describe the light-dependent reactions."
    assert result.prerequisites == ["Cell biology basics"]


@pytest.mark.asyncio
async def test_well_formed_payload_with_empty_prerequisites() -> None:
    response = _make_valid_response(prerequisites=[])
    client = StubModelClient(response)
    refiner = LLMRefiner(client)

    result = await refiner.refine(_make_node())

    assert result.prerequisites == []
    assert result.provenance == "llm_refined"


# ---------------------------------------------------------------------------
# Source spans preserved unchanged
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_source_spans_preserved() -> None:
    node = _make_node()
    original_spans = node.source_spans

    client = StubModelClient(_make_valid_response())
    refiner = LLMRefiner(client)
    result = await refiner.refine(node)

    assert result.source_spans == original_spans
    assert result.id == node.id


# ---------------------------------------------------------------------------
# Malformed payloads → LLMRefinerError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_malformed_json_raises_llm_refiner_error() -> None:
    client = StubModelClient("not valid json at all")
    refiner = LLMRefiner(client)

    with pytest.raises(LLMRefinerError, match="invalid JSON"):
        await refiner.refine(_make_node())


@pytest.mark.asyncio
async def test_missing_required_field_raises_llm_refiner_error() -> None:
    # "summary" is absent
    response = json.dumps(
        {
            "title": "Photosynthesis",
            "learning_objective": "Explain it.",
            "prerequisites": [],
        }
    )
    client = StubModelClient(response)
    refiner = LLMRefiner(client)

    with pytest.raises(LLMRefinerError, match="schema validation"):
        await refiner.refine(_make_node())


@pytest.mark.asyncio
async def test_wrong_type_for_prerequisites_raises_llm_refiner_error() -> None:
    # prerequisites must be list[str], not a plain string
    response = json.dumps(
        {
            "title": "X",
            "summary": "Y",
            "learning_objective": "Z",
            "prerequisites": "not a list",
        }
    )
    client = StubModelClient(response)
    refiner = LLMRefiner(client)

    with pytest.raises(LLMRefinerError, match="schema validation"):
        await refiner.refine(_make_node())


# ---------------------------------------------------------------------------
# Long text truncation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_long_text_is_truncated_before_sending() -> None:
    long_summary = "x" * 5000
    node = _make_node(summary=long_summary)

    client = StubModelClient(_make_valid_response())
    refiner = LLMRefiner(client)
    await refiner.refine(node)

    assert len(client.calls) == 1
    user_message = next(m for m in client.calls[0] if m["role"] == "user")
    # Truncation sentinel must appear in the user message content
    assert "[TEXT TRUNCATED]" in user_message["content"]
    # Full 5000-char summary must NOT appear verbatim
    assert long_summary not in user_message["content"]


@pytest.mark.asyncio
async def test_short_text_is_not_truncated() -> None:
    node = _make_node(summary="Short summary.")

    client = StubModelClient(_make_valid_response())
    refiner = LLMRefiner(client)
    await refiner.refine(node)

    user_message = next(m for m in client.calls[0] if m["role"] == "user")
    assert "[TEXT TRUNCATED]" not in user_message["content"]
    assert "Short summary." in user_message["content"]
