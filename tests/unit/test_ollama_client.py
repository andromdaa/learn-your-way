"""Unit tests for OllamaModelClient.

All HTTP calls are intercepted by httpx.MockTransport — no running Ollama required.
"""

import json
from typing import Any

import httpx
import pytest

from lesson_graph.interfaces import ChatMessage, ModelClient
from lyw_core.clients import OllamaModelClient
from lyw_core.clients.ollama import OllamaError

_TEST_MODEL = "gemma3:4b"


def _make_response(content: str, status: int = 200) -> bytes:
    """Build a minimal Ollama /api/chat response body."""
    body: dict[str, Any] = {
        "message": {"role": "assistant", "content": content},
        "done": True,
    }
    return json.dumps(body).encode()


def _make_transport(content: str, status: int = 200) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=_make_response(content, status))

    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_protocol_assignment() -> None:
    client = OllamaModelClient(base_url="http://localhost:11434", model=_TEST_MODEL)
    _: ModelClient = client  # static check: satisfies ModelClient protocol


# ---------------------------------------------------------------------------
# Successful completion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_returns_content() -> None:
    transport = _make_transport("Hello, learner!")
    client = OllamaModelClient(
        base_url="http://localhost:11434",
        model=_TEST_MODEL,
        transport=transport,
    )
    messages: list[ChatMessage] = [{"role": "user", "content": "Hi"}]
    result = await client.complete(messages)
    assert result == "Hello, learner!"


@pytest.mark.asyncio
async def test_complete_sends_correct_payload() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, content=_make_response("ok"))

    client = OllamaModelClient(
        base_url="http://localhost:11434",
        model=_TEST_MODEL,
        transport=httpx.MockTransport(handler),
    )
    messages: list[ChatMessage] = [
        {"role": "system", "content": "You are a tutor."},
        {"role": "user", "content": "Explain entropy."},
    ]
    await client.complete(messages, temperature=0.3, max_tokens=512)

    assert len(captured) == 1
    payload = json.loads(captured[0].content)
    assert payload["model"] == _TEST_MODEL
    assert payload["messages"] == messages
    assert payload["stream"] is False
    assert payload["options"]["temperature"] == 0.3
    assert payload["options"]["num_predict"] == 512


@pytest.mark.asyncio
async def test_complete_omits_num_predict_when_max_tokens_none() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, content=_make_response("ok"))

    client = OllamaModelClient(
        base_url="http://localhost:11434",
        model=_TEST_MODEL,
        transport=httpx.MockTransport(handler),
    )
    await client.complete([{"role": "user", "content": "hi"}], max_tokens=None)

    payload = json.loads(captured[0].content)
    assert "num_predict" not in payload.get("options", {})


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_200_raises_ollama_error() -> None:
    transport = _make_transport("", status=500)
    client = OllamaModelClient(
        base_url="http://localhost:11434",
        model=_TEST_MODEL,
        transport=transport,
    )
    with pytest.raises(OllamaError) as exc_info:
        await client.complete([{"role": "user", "content": "hi"}])

    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_404_raises_ollama_error_with_status() -> None:
    transport = _make_transport("not found", status=404)
    client = OllamaModelClient(
        base_url="http://localhost:11434",
        model=_TEST_MODEL,
        transport=transport,
    )
    with pytest.raises(OllamaError) as exc_info:
        await client.complete([{"role": "user", "content": "hi"}])

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Configurable timeout / retries
# ---------------------------------------------------------------------------


def test_default_timeout_and_retries() -> None:
    client = OllamaModelClient(base_url="http://localhost:11434", model=_TEST_MODEL)
    assert client.timeout > 0
    assert client.max_retries >= 0


def test_custom_timeout_and_retries() -> None:
    client = OllamaModelClient(
        base_url="http://localhost:11434",
        model=_TEST_MODEL,
        timeout=120.0,
        max_retries=5,
    )
    assert client.timeout == 120.0
    assert client.max_retries == 5


# ---------------------------------------------------------------------------
# OllamaError attributes
# ---------------------------------------------------------------------------


def test_ollama_error_carries_structured_attributes() -> None:
    # OllamaError used to require a __reduce__ override for Arq pickle
    # round-trips. After AND-33, personalize_concept catches OllamaError at
    # the job boundary and converts it to Failure(code="ollama_error", ...),
    # so the exception never reaches Redis. The pickle round-trip test is no
    # longer applicable; what matters is that structured attributes are
    # accessible for building the Failure payload.
    err = OllamaError(503, "service unavailable: model loading")
    assert err.status_code == 503
    assert err.body == "service unavailable: model loading"
    assert "503" in str(err)
