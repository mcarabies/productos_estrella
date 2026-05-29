"""
Structured logging configuration — structlog.
Produces JSON output in production, pretty console in development.
"""
from __future__ import annotations

import logging
import sys

import structlog

from app.core.config import Environment, settings


def configure_logging() -> None:
    """Configure structlog with appropriate renderers per environment."""
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.app_env == Environment.development:
        # Human-readable in development
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer()
    else:
        # JSON in production (parse-friendly for log aggregators)
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())

    # Silence noisy libraries
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.app_debug else logging.WARNING
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a named structlog logger."""
    return structlog.get_logger(name)
