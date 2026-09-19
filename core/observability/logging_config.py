"""Structured (JSON) logging, real stdlib `logging` underneath — no
external log-shipping dependency. Every log line is a single JSON object
with a stable set of base fields plus whatever structured context a
caller attaches via `logger.info(..., extra={...})`, so log lines are
machine-parseable (by a real log aggregator, or by this module's own
`parse_log_line` used in tests) rather than freeform text.
"""
from __future__ import annotations

import json
import logging
import sys

_RESERVED_LOG_RECORD_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename", "module",
    "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs",
    "relativeCreated", "thread", "threadName", "processName", "process", "message",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_RECORD_ATTRS and key not in payload:
                payload[key] = value

        return json.dumps(payload, default=str)


def configure_json_logging(level: int = logging.INFO, stream=None) -> logging.Handler:
    """Replaces the root logger's handlers with a single JSON-formatting
    stream handler. Returns the handler so callers (and tests) can attach
    it elsewhere or swap its stream.
    """
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    return handler


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def parse_log_line(line: str) -> dict:
    """Parses a line this module actually produced — used by tests to
    verify real output, not to validate arbitrary third-party log text.
    """
    return json.loads(line)
