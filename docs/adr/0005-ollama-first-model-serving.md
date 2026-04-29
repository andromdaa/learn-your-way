# ADR-0005: Ollama-first model serving with API fallback

## Status

Accepted.

## Context

The system needs a chat-completion model for concept extraction,
re-leveling, example replacement, quiz generation, slide outlining,
and gap-detector reasoning. Two deployment shapes are realistic for a
self-hosted single-user tool:

1. Local inference on the user's machine (privacy-preserving, free
   per-call, requires local GPU or patience).
2. A remote chat-completion API (no local hardware requirement, paid
   per-call, requires network).

Both must be supported without forking the codebase.

## Decision

- Default to Ollama running Gemma 4 locally.
- Define a `ModelClient` Protocol in
  `src/lesson_graph/interfaces/model_client.py` so concrete
  implementations (Ollama, Anthropic, OpenAI-compatible) are
  swappable behind a single typed interface.
- Configuration selects the client at startup via pydantic-settings.

## Consequences

Positive:

- The default deployment runs entirely offline once weights are
  pulled.
- Switching to a remote API is a config change, not a code change.
- The Protocol forces all clients to share the same call shape,
  preventing prompt code from coupling to a specific provider's
  request/response format.

Negative:

- Concrete clients must each implement retries, timeouts, and
  rate-limit handling against the same Protocol surface. Some
  duplication is unavoidable.
- Local Gemma 4 inference is bounded by the user's hardware. Quality
  on consumer GPUs is acceptable but slower than a cloud model.

## Alternatives considered

**Cloud API by default (Anthropic / OpenAI / Gemini).** Faster and
higher-quality out of the box, but introduces a hard network
dependency and per-call cost. For a self-hosted personal tool, that
is the wrong default.

**Direct llama.cpp integration.** Lower-level than Ollama and gives
finer control over inference. Ollama wraps llama.cpp with model
management, hot-swapping, and a stable HTTP API; the abstraction is
worth the dependency.

**Hand-rolled HTTP client per provider, no Protocol.** Faster to
write at first, brittle later. The Protocol is a 30-line file that
prevents the two implementations from drifting.
