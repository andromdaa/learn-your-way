"""Unit tests for lyw_core.worker.settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

_TEST_MODEL = "gemma3:4b"


async def test_startup_registers_progress_factory() -> None:
    from lyw_core.worker.settings import startup

    mock_data_dir = MagicMock()
    ctx: dict[str, Any] = {"redis": AsyncMock()}

    with (
        patch("lyw_core.worker.settings._ingest_startup", new_callable=AsyncMock),
        patch("lyw_core.worker.settings.Settings") as mock_settings,
        patch("lyw_core.clients.OllamaModelClient"),
        patch("lyw_core.storage.fs.DataDir", return_value=mock_data_dir),
    ):
        mock_settings.return_value.ollama_base_url = "http://localhost:11434"
        mock_settings.return_value.model_name = _TEST_MODEL
        mock_settings.return_value.data_dir = Path("./data")
        await startup(ctx)

    assert "progress_factory" in ctx
    assert "model_client" in ctx
    assert ctx["data_dir"] is mock_data_dir
    mock_data_dir.bootstrap.assert_called_once()


async def test_startup_progress_factory_returns_job_progress() -> None:
    from lyw_core.worker.settings import startup

    ctx: dict[str, Any] = {"redis": AsyncMock()}

    with (
        patch("lyw_core.worker.settings._ingest_startup", new_callable=AsyncMock),
        patch("lyw_core.worker.settings.Settings"),
        patch("lyw_core.clients.OllamaModelClient"),
        patch("lyw_core.storage.fs.DataDir"),
    ):
        await startup(ctx)

    from lyw_core.worker.jobs._progress import JobProgress

    progress = ctx["progress_factory"]("job-1")
    assert isinstance(progress, JobProgress)


async def test_startup_progress_factory_with_lesson_id() -> None:
    from lyw_core.worker.settings import startup

    ctx: dict[str, Any] = {"redis": AsyncMock()}

    with (
        patch("lyw_core.worker.settings._ingest_startup", new_callable=AsyncMock),
        patch("lyw_core.worker.settings.Settings"),
        patch("lyw_core.clients.OllamaModelClient"),
        patch("lyw_core.storage.fs.DataDir"),
    ):
        await startup(ctx)

    from lyw_core.worker.jobs._progress import JobProgress

    progress = ctx["progress_factory"]("job-1", lesson_id="l1")
    assert isinstance(progress, JobProgress)


async def test_shutdown_delegates_to_ingest_shutdown() -> None:
    from lyw_core.worker.settings import shutdown

    ctx: dict[str, Any] = {"db": AsyncMock()}

    with patch(
        "lyw_core.worker.settings._ingest_shutdown", new_callable=AsyncMock
    ) as mock_sd:
        await shutdown(ctx)

    mock_sd.assert_awaited_once_with(ctx)


def test_worker_settings_has_correct_functions() -> None:
    from lyw_core.worker.jobs.ingest import ingest_source
    from lyw_core.worker.jobs.personalize import personalize_concept
    from lyw_core.worker.settings import WorkerSettings

    assert ingest_source in WorkerSettings.functions
    assert personalize_concept in WorkerSettings.functions
    assert WorkerSettings.on_startup is not None
    assert WorkerSettings.on_shutdown is not None
    assert WorkerSettings.redis_settings is not None
