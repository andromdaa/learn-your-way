"""End-to-end smoke test: ingest → concept count → personalize round-trip.

Validates that the full pipeline from PDF to personalized asset works,
and that exceptions raised inside personalize_concept propagate cleanly
rather than crashing the worker (the "not 500" contract).

Requires Docker (Testcontainers boots Qdrant).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from qdrant_client import QdrantClient

from lyw_core.clients.ollama import OllamaError
from lyw_core.db.dao import Database
from lyw_core.profiles.models import LearnerProfile
from lyw_core.retrieval.bm25 import BM25Retriever
from lyw_core.retrieval.embedding import EmbeddingModel
from lyw_core.storage.fs import DataDir

_CI_SMOKE_PDF = Path(__file__).parent.parent / "fixtures" / "ci_smoke.pdf"
_PROFILE_ID = "smoke_profile"

_CONCEPT_COUNT_LOW = 5
_CONCEPT_COUNT_HIGH = 60


class _FakeModelClient:
    """Minimal ModelClient stub that returns a canned string."""

    def __init__(self, response: str = "Canned model response for testing.") -> None:
        self._response = response

    async def complete(
        self,
        messages: list[Any],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> str:
        return self._response


class _RaisingModelClient:
    """ModelClient stub that raises OllamaError on every call."""

    async def complete(
        self,
        messages: list[Any],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> str:
        raise OllamaError(500, "simulated inference failure")


@pytest.fixture(scope="module")
def embedding() -> EmbeddingModel:
    return EmbeddingModel()


@pytest.fixture
async def db(tmp_path: Path) -> AsyncGenerator[Database, None]:
    # Use yield so aiosqlite's worker thread is stopped cleanly after each
    # test. Without close(), the daemon thread blocks on queue.Queue.get()
    # during Python 3.12's threading._shutdown(), preventing process exit.
    database = await Database.connect(str(tmp_path / "smoke.db"))
    yield database
    await database.close()


@pytest.fixture
def data_dir(tmp_path: Path) -> DataDir:
    d = DataDir(tmp_path / "data")
    d.bootstrap()
    return d


@pytest.mark.integration
@pytest.mark.timeout(300)
async def test_smoke_concept_count_in_range(
    db: Database,
    qdrant_client: QdrantClient,
    embedding: EmbeddingModel,
) -> None:
    """Ingest the CI smoke fixture and assert the chunker yields 5-60 concepts.

    Outside this band is a regression signal: too few means the parser
    is dropping sections; too many means the chunker is over-extracting.
    """
    from lyw_core.worker.jobs.ingest import ingest_source

    ctx: dict[str, Any] = {
        "db": db,
        "bm25_retriever": BM25Retriever(),
        "qdrant_client": qdrant_client,
        "embedding": embedding,
    }
    # Use a unique doc_id so the Qdrant collection name doesn't collide with
    # the other smoke tests, which share the same module-scoped qdrant_client.
    result = await ingest_source(
        ctx, source_path=str(_CI_SMOKE_PDF), doc_id="ci_smoke_count"
    )
    count = result["concept_count"]
    assert _CONCEPT_COUNT_LOW <= count <= _CONCEPT_COUNT_HIGH, (
        f"Expected {_CONCEPT_COUNT_LOW}-{_CONCEPT_COUNT_HIGH} concepts, "
        f"got {count}. Regression in chunker or parser."
    )


@pytest.mark.integration
@pytest.mark.timeout(300)
async def test_smoke_personalize_relevel_succeeds(
    db: Database,
    qdrant_client: QdrantClient,
    embedding: EmbeddingModel,
    data_dir: DataDir,
) -> None:
    """Successful relevel round-trip: fake model returns text, asset is persisted."""
    from lyw_core.worker.jobs.ingest import ingest_source
    from lyw_core.worker.jobs.personalize import personalize_concept

    doc_id = "ci_smoke_relevel"
    lesson_id = f"lesson_{doc_id}"

    ingest_ctx: dict[str, Any] = {
        "db": db,
        "bm25_retriever": BM25Retriever(),
        "qdrant_client": qdrant_client,
        "embedding": embedding,
    }
    await ingest_source(ingest_ctx, source_path=str(_CI_SMOKE_PDF), doc_id=doc_id)

    graph = await db.get_lesson_graph(lesson_id)
    assert graph is not None and graph.concepts
    concept_id = graph.concepts[0].id

    profile = LearnerProfile(
        id=_PROFILE_ID,
        grade_level="8th grade",
        interests=["mathematics"],
        goals=["understand algebra"],
    )
    await db.add_profile(profile)

    personalize_ctx: dict[str, Any] = {
        "db": db,
        "data_dir": data_dir,
        "model_client": _FakeModelClient(),
    }
    result = await personalize_concept(
        personalize_ctx,
        lesson_id=lesson_id,
        concept_id=concept_id,
        profile_id=_PROFILE_ID,
        kind="relevel",
    )
    from lyw_core.worker.result import Success

    assert isinstance(result, Success)
    assert "asset_id" in result.payload
    assert Path(result.payload["file_path"]).exists()


@pytest.mark.integration
@pytest.mark.timeout(300)
async def test_smoke_personalize_ollama_error_returns_failure(
    db: Database,
    qdrant_client: QdrantClient,
    embedding: EmbeddingModel,
    data_dir: DataDir,
) -> None:
    """When the model raises OllamaError, personalize_concept returns a typed Failure.

    This is the "not 500" contract: the error leaves the job function as a
    typed Failure (not an unhandled crash), so Arq pickles the Pydantic model
    cleanly and the API returns status="failed" rather than HTTP 500.
    """
    from lyw_core.worker.jobs.ingest import ingest_source
    from lyw_core.worker.jobs.personalize import personalize_concept
    from lyw_core.worker.result import Failure

    doc_id = "ci_smoke_error"
    lesson_id = f"lesson_{doc_id}"

    ingest_ctx: dict[str, Any] = {
        "db": db,
        "bm25_retriever": BM25Retriever(),
        "qdrant_client": qdrant_client,
        "embedding": embedding,
    }
    await ingest_source(ingest_ctx, source_path=str(_CI_SMOKE_PDF), doc_id=doc_id)

    graph = await db.get_lesson_graph(lesson_id)
    assert graph is not None and graph.concepts
    concept_id = graph.concepts[0].id

    profile = LearnerProfile(
        id=_PROFILE_ID,
        grade_level="8th grade",
        interests=["mathematics"],
        goals=["understand algebra"],
    )
    await db.add_profile(profile)

    personalize_ctx: dict[str, Any] = {
        "db": db,
        "data_dir": data_dir,
        "model_client": _RaisingModelClient(),
    }
    result = await personalize_concept(
        personalize_ctx,
        lesson_id=lesson_id,
        concept_id=concept_id,
        profile_id=_PROFILE_ID,
        kind="relevel",
    )
    assert isinstance(result, Failure)
    assert result.code == "ollama_error"
    assert result.details["status_code"] == 500
