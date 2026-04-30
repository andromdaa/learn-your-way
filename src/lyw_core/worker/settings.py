"""Arq WorkerSettings for the ingest worker."""

from collections.abc import Callable
from typing import Any, ClassVar

from arq.connections import RedisSettings

from lyw_core.settings import Settings
from lyw_core.worker.jobs.ingest import ingest_source
from lyw_core.worker.jobs.ingest import shutdown as _ingest_shutdown
from lyw_core.worker.jobs.ingest import startup as _ingest_startup
from lyw_core.worker.jobs.personalize import personalize_concept


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(Settings().redis_url)


async def startup(ctx: dict[str, Any]) -> None:
    """Initialise shared context for all jobs."""
    await _ingest_startup(ctx)

    cfg = Settings()

    from lyw_core.clients import OllamaModelClient
    from lyw_core.storage.fs import DataDir

    ctx["model_client"] = OllamaModelClient(
        base_url=cfg.ollama_base_url,
        model=cfg.model_name,
    )
    data_dir = DataDir(cfg.data_dir)
    data_dir.bootstrap()
    ctx["data_dir"] = data_dir


async def shutdown(ctx: dict[str, Any]) -> None:
    await _ingest_shutdown(ctx)


class WorkerSettings:
    functions: ClassVar[list[Callable[..., object]]] = [
        ingest_source,
        personalize_concept,
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings()
