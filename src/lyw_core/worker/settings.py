"""Arq WorkerSettings for the ingest worker."""

from collections.abc import Callable
from typing import ClassVar

from arq.connections import RedisSettings

from lyw_core.settings import Settings
from lyw_core.worker.jobs.ingest import ingest_source, shutdown, startup


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(Settings().redis_url)


class WorkerSettings:
    functions: ClassVar[list[Callable[..., object]]] = [ingest_source]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings()
