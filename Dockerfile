# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Install dependencies into an isolated layer so rebuilds are fast.
# The cache mount persists downloaded wheels across builds so a transient
# PyPI timeout on one attempt doesn't re-download everything next time.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_HTTP_TIMEOUT=120 uv sync --frozen --no-dev --no-install-project

# Copy source and install the project itself
COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_HTTP_TIMEOUT=120 uv sync --frozen --no-dev

# ---- runtime image -------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

# Copy the virtualenv from the builder (no uv required at runtime)
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app/src"

EXPOSE 8000
