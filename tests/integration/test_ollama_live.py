"""Live integration test for OllamaModelClient.

Skipped unless a real Ollama instance is reachable at LYW_OLLAMA_BASE_URL
(default: http://localhost:11434).  Run with::

    pytest -m integration tests/integration/test_ollama_live.py
"""

import pytest

from lyw_core.clients import OllamaModelClient
from lyw_core.clients.ollama import OllamaError
from lyw_core.settings import Settings


def _ollama_reachable(base_url: str) -> bool:
    import httpx

    try:
        httpx.get(f"{base_url}/api/tags", timeout=2.0)
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def settings() -> Settings:
    return Settings()


@pytest.mark.integration
async def test_live_complete_returns_string(settings: Settings) -> None:
    if not _ollama_reachable(settings.ollama_base_url):
        pytest.skip("Ollama not reachable")

    client = OllamaModelClient(
        base_url=settings.ollama_base_url,
        model=settings.model_name,
        timeout=30.0,
    )
    result = await client.complete(
        [{"role": "user", "content": "Reply with exactly: pong"}],
        temperature=0.0,
        max_tokens=16,
    )
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.integration
async def test_live_bad_model_raises_ollama_error(settings: Settings) -> None:
    if not _ollama_reachable(settings.ollama_base_url):
        pytest.skip("Ollama not reachable")

    client = OllamaModelClient(
        base_url=settings.ollama_base_url,
        model="nonexistent-model-xyz:latest",
        timeout=10.0,
        max_retries=0,
    )
    with pytest.raises(OllamaError):
        await client.complete([{"role": "user", "content": "hi"}])
