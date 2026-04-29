import logging

import structlog

from lyw_core.settings import Settings


def configure_logging(settings: Settings | None = None) -> None:
    """Configure structlog for the application.

    Console rendering by default; JSON when settings.log_format == "json".
    Bridges stdlib logging so third-party libraries share the same pipeline.
    Safe to call repeatedly.
    """
    if settings is None:
        settings = Settings()

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]

    if settings.log_format == "json":
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
        force=True,
    )
