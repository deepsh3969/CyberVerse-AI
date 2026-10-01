"""Structured logging with request correlation.

`LOG_FORMAT=json` (default in production) emits one JSON object per line so
logs can be shipped to any aggregator; `LOG_FORMAT=text` keeps human-friendly
development output. A contextvar carries the request id so every line emitted
while handling a request is correlated.
"""
from __future__ import annotations

import contextvars
import json
import logging
import sys
import time
from typing import Any

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

_RESERVED = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename", "module",
    "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs",
    "relativeCreated", "thread", "threadName", "processName", "process", "taskName",
    "message", "asctime",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
            + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        for key, value in record.__dict__.items():
            if key in _RESERVED or key.startswith("_"):
                continue
            payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging() -> None:
    if getattr(logging, "_cyberverse_configured", False):
        return
    root = logging.getLogger()
    root.setLevel(os_level())
    handler = logging.StreamHandler(sys.stdout)
    if logger_format() == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-7s %(name)s %(message)s")
        )
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False
    setattr(logging, "_cyberverse_configured", True)


def os_level() -> int:
    from app.core.config import settings

    return getattr(logging, settings.log_level, logging.INFO)


def logger_format() -> str:
    from app.core.config import settings

    return settings.log_format
