"""Stderr JSON logging with secret redaction."""

from __future__ import annotations

import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from platformdirs import user_log_dir

_REDACT_KEYS = {"authorization", "api_key", "password", "token", "jwt"}


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        skip = {"args", "msg", "exc_info", "exc_text", "stack_info", "stack_level"}
        for k, v in record.__dict__.items():
            if k in payload or k.startswith("_") or k in skip:
                continue
            if k.lower() in _REDACT_KEYS:
                payload[k] = "***"
            elif isinstance(v, str | int | float | bool) or v is None:
                payload[k] = v
        return json.dumps(payload, default=str)


def configure_logging(level: str | None = None) -> None:
    level_name = (level or os.environ.get("OCTOPUS_MCP_LOG_LEVEL") or "INFO").upper()
    root = logging.getLogger()
    root.setLevel(level_name)

    stderr = logging.StreamHandler(sys.stderr)
    stderr.setFormatter(_JsonFormatter())
    root.handlers = [stderr]

    log_dir = Path(user_log_dir("octopus-mcp"))
    log_dir.mkdir(parents=True, exist_ok=True)
    fh = RotatingFileHandler(log_dir / "server.log", maxBytes=10 * 1024 * 1024, backupCount=5)
    fh.setFormatter(_JsonFormatter())
    root.addHandler(fh)
