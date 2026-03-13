"""Structured JSON logging configuration."""

from __future__ import annotations

import logging
import sys


class RequestIdFilter(logging.Filter):
    """Inject request_id from Flask's request context into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            from flask import g

            record.request_id = getattr(g, "request_id", "-")
        except Exception:
            record.request_id = "-"
        return True


def setup_logging(level: str = "INFO") -> None:
    """Configure structured JSON logging. Falls back to plain text if python-json-logger is unavailable."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    try:
        from pythonjsonlogger import jsonlogger

        handler = logging.StreamHandler(sys.stdout)
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
            rename_fields={"asctime": "time", "levelname": "level", "name": "logger"},
        )
        handler.setFormatter(formatter)
        handler.addFilter(RequestIdFilter())

        root = logging.getLogger()
        root.handlers.clear()
        root.addHandler(handler)
        root.setLevel(numeric_level)

    except ImportError:
        logging.basicConfig(
            level=numeric_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )
        logging.getLogger(__name__).warning(
            "python-json-logger not installed — using plain text logging. "
            "Install with: pip install python-json-logger"
        )
