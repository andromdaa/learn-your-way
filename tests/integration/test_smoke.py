"""End-to-end smoke test: ingest → concept count → personalize round-trip.

Validates that the full pipeline from PDF to personalized asset works,
and that exceptions raised inside personalize_concept propagate cleanly
rather than crashing the worker (the "not 500" contract).

Requires Docker (Testcontainers boots Qdrant and Redis as needed).
"""

from __future__ import annotations

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
_DOC_ID = "ci_smoke"
_LESSON_ID = f"lesson_{_DOC_ID}"
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
async def db(tmp_path: Path) -> Database:
    return await Database.connect(str(tmp_path / "smoke.db"))


@pytest.fixture
def data_dir(tmp_path: Path) -> DataDir:
    d = DataDir(tmp_path / "data")
    d.bootstrap()
    return d


@pytest.mark.integration
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
    result = await ingest_source(ctx, source_path=str(_CI_SMOKE_PDF), doc_id=_DOC_ID)
    count = result["concept_count"]
    assert _CONCEPT_COUNT_LOW <= count <= _CONCEPT_COUNT_HIGH, (
        f"Expected {_CONCEPT_COUNT_LOW}-{_CONCEPT_COUNT_HIGH} concepts, "
        f"got {count}. Regression in chunker or parser."
    )


@pytest.mark.integration
async def test_smoke_personalize_relevel_succeeds(
    db: Database,
    qdrant_client: QdrantClient,
    embedding: EmbeddingModel,
    data_dir: DataDir,
) -> None:
    """Successful relevel round-trip: fake model returns text, asset is persisted."""
    from lyw_core.worker.jobs.ingest import ingest_source
    from lyw_core.worker.jobs.personalize import personalize_concept

    ingest_ctx: dict[str, Any] = {
        "db": db,
        "bm25_retriever": BM25Retriever(),
        "qdrant_client": qdrant_client,
        "embedding": embedding,
    }
    await ingest_source(ingest_ctx, source_path=str(_CI_SMOKE_PDF), doc_id=_DOC_ID)

    graph = await db.get_lesson_graph(_LESSON_ID)
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
        lesson_id=_LESSON_ID,
        concept_id=concept_id,
        profile_id=_PROFILE_ID,
        kind="relevel",
    )
    assert "asset_id" in result
    assert Path(result["file_path"]).exists()


@pytest.mark.integration
async def test_smoke_personalize_exception_propagates(
    db: Database,
    qdrant_client: QdrantClient,
    embedding: EmbeddingModel,
    data_dir: DataDir,
) -> None:
    """When the model raises OllamaError, personalize_concept propagates it cleanly.

    This is the "not 500" contract: the exception leaves the job function
    as a typed exception (not an unhandled crash), so arq can pickle it
    into Redis and the API can return status="failed" rather than HTTP 500.
    The pickle invariant test in test_pickle_invariant.py separately verifies
    that OllamaError survives the Redis round-trip.
    """
    from lyw_core.worker.jobs.ingest import ingest_source
    from lyw_core.worker.jobs.personalize import personalize_concept

    ingest_ctx: dict[str, Any] = {
        "db": db,
        "bm25_retriever": BM25Retriever(),
        "qdrant_client": qdrant_client,
        "embedding": embedding,
    }
    await ingest_source(ingest_ctx, source_path=str(_CI_SMOKE_PDF), doc_id=_DOC_ID)

    graph = await db.get_lesson_graph(_LESSON_ID)
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
    with pytest.raises(OllamaError) as exc_info:
        await personalize_concept(
            personalize_ctx,
            lesson_id=_LESSON_ID,
            concept_id=concept_id,
            profile_id=_PROFILE_ID,
            kind="relevel",
        )
    assert exc_info.value.status_code == 500
