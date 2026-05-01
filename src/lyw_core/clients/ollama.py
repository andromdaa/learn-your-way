"""Ollama async chat-completion client."""

from typing import Any

import httpx

from lesson_graph.interfaces import ChatMessage


class OllamaError(Exception):
    """Raised when the Ollama API returns a non-200 response."""

    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"Ollama returned HTTP {status_code}: {body[:200]}")

    def __reduce__(self) -> tuple[Any, tuple[int, str]]:
        # Pickle protocol: ensure round-trip through Arq's result store
        # reconstructs the exception with both required positional args.
        return (self.__class__, (self.status_code, self.body))


class OllamaModelClient:
    """Async chat-completion client for a local Ollama instance.

    Satisfies the ``ModelClient`` protocol from ``lesson_graph.interfaces``.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout: float = 60.0,
        max_retries: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self._transport = transport

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> str:
        options: dict[str, Any] = {"temperature": temperature}
        if max_tokens is not None:
            options["num_predict"] = max_tokens

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": options,
        }

        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._post(payload)
                if response.status_code != 200:
                    raise OllamaError(response.status_code, response.text)
                data = response.json()
                return str(data["message"]["content"])
            except OllamaError:
                raise
            except Exception as exc:
                last_exc = exc
                if attempt == self.max_retries:
                    break

        raise last_exc or RuntimeError("unreachable")

    async def _post(self, payload: dict[str, Any]) -> httpx.Response:
        kwargs: dict[str, Any] = {
            "timeout": self.timeout,
        }
        if self._transport is not None:
            kwargs["transport"] = self._transport

        async with httpx.AsyncClient(**kwargs) as client:
            return await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
