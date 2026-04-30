"""Shared integration-test fixtures."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from qdrant_client import QdrantClient
from testcontainers.qdrant import QdrantContainer

_QDRANT_IMAGE = "qdrant/qdrant:v1.17.0"


@pytest.fixture(scope="module")
def qdrant_client() -> Generator[QdrantClient, None, None]:
    try:
        with QdrantContainer(image=_QDRANT_IMAGE) as container:
            url = (
                f"http://{container.get_container_host_ip()}"
                f":{container.get_exposed_port(6333)}"
            )
            yield QdrantClient(url=url)
    except Exception:
        pytest.skip("Docker not available")
