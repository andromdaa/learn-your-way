"""Model client protocol.

Defines the interface that every concrete model client implementation
(Ollama, Anthropic API, OpenAI-compatible API, etc.) must satisfy.
This module deliberately contains no implementations; concrete clients
live alongside their dependencies in later phases.

Defining the Protocol up front prevents Ollama and remote-API code
paths from drifting in shape as they are added.
"""

from typing import Literal, Protocol, TypedDict


class ChatMessage(TypedDict):
    """A single message in a chat-completion exchange.

    ``role`` is one of ``"system"``, ``"user"``, or ``"assistant"``.
    The string is left untyped to keep the protocol broad; concrete
    clients enforce their own role vocabulary.
    """

    role: Literal["system", "user", "assistant"]
    content: str


class ModelClient(Protocol):
    """Async chat-completion client.

    All implementations are async because the surrounding stack
    (FastAPI + Arq) is asyncio-based. Synchronous wrappers, if needed,
    can be added per implementation.
    """

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> str:
        """Run a chat completion and return the model's text output.

        Implementations are responsible for retries, timeouts, and any
        provider-specific error handling. The protocol guarantees only
        the shape of the call and the type of the return.
        """
        ...
