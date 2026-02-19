"""Structured JSON logging for Gauntlet detection events.

Provides a JSON formatter, setup helper, and detection event logger.
All detection events log a SHA-256 hash of the input — never raw text.
"""

import hashlib
import json
import logging
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "_gauntlet_extra"):
            log_data.update(record._gauntlet_extra)
        return json.dumps(log_data, default=str)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the ``gauntlet`` logger with JSON output to stderr.

    Idempotent — calling multiple times is safe.
    """
    logger = logging.getLogger("gauntlet")
    if logger.handlers:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False


def _log_detection_event(
    text: str,
    layer: int,
    latency_ms: float,
    is_injection: bool,
    attack_type: str | None,
    confidence: float,
) -> None:
    """Log a detection event with privacy-safe input hash."""
    logger = logging.getLogger("gauntlet")
    text_hash = hashlib.sha256(text.encode()).hexdigest()
    extra = {
        "_gauntlet_extra": {
            "event": "detection",
            "input_hash": text_hash,
            "input_length": len(text),
            "layer": layer,
            "latency_ms": round(latency_ms, 2),
            "is_injection": is_injection,
            "attack_type": attack_type,
            "confidence": confidence,
        }
    }
    logger.info("detection_event", extra=extra)
