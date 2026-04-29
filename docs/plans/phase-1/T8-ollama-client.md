# T8 - OllamaModelClient Implementing ModelClient

## Status

- [ ] T8: `OllamaModelClient` implementing the `ModelClient` protocol

## Goal

Land the default async chat-completion client from ADR-0005. The
`ModelClient` protocol already lives in `lesson_graph.interfaces`;
this task adds the Ollama implementation under `lyw_core.clients`.

## Files

- Create `src/lyw_core/clients/__init__.py`.
- Create `src/lyw_core/clients/ollama.py` using `httpx`.
- Include configurable retries and timeout.
- Raise a typed error on non-200 responses.
- Create `tests/unit/test_ollama_client.py` with `httpx` mock
  transport.
- Assert protocol satisfaction with an explicit
  `_: ModelClient = OllamaModelClient(...)`.
- Modify `.env.example` with Ollama base URL and model name fields.

## Depends On

- T1 for settings.
- `httpx` added in T3.

## Acceptance

- `uv run pytest tests/unit/test_ollama_client.py` passes with mocked
  `httpx`.
- `uv run mypy` is strict-clean and validates the protocol check.
- The optional live Ollama integration path skips cleanly without a
  running Ollama.

## Out of Scope

- Anthropic or OpenAI-compatible clients.
- Streaming responses.
- Rate-limit-aware backoff beyond simple retries.

## Risk Notes

- None recorded.
