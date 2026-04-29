"""Tests for the ModelClient Protocol.

The Protocol itself has no runtime behavior to test. These tests pin
down its structural shape so that any drift between the Protocol and
its eventual implementations is caught at type-check time.
"""

from collections.abc import Iterable

from lesson_graph import ChatMessage, ModelClient


def test_chat_message_typed_dict_keys() -> None:
    msg: ChatMessage = {"role": "system", "content": "you are a tutor"}
    assert msg["role"] == "system"
    assert msg["content"] == "you are a tutor"


class _StubClient:
    """Structural conformer used to verify the Protocol shape."""

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> str:
        del messages, temperature, max_tokens
        return ""


def _accepts_client(client: ModelClient) -> ModelClient:
    return client


def test_protocol_accepts_structural_conformer() -> None:
    # If the Protocol shape changes, this assignment will fail to
    # type-check under mypy strict, even though it succeeds at runtime.
    client = _accepts_client(_StubClient())
    assert client is not None


def test_chat_message_is_iterable_dict() -> None:
    msg: ChatMessage = {"role": "user", "content": "hello"}
    keys: Iterable[str] = msg.keys()
    assert set(keys) == {"role", "content"}
