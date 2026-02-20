"""Tests for Gauntlet structured JSON logging."""

import hashlib
import json
import logging

import pytest

from gauntlet._logging import JSONFormatter, _log_detection_event, setup_logging


class TestJSONFormatter:
    """Tests for JSONFormatter."""

    def test_output_is_valid_json(self) -> None:
        record = logging.LogRecord(
            name="gauntlet",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello",
            args=(),
            exc_info=None,
        )
        fmt = JSONFormatter()
        out = fmt.format(record)
        data = json.loads(out)
        assert data["message"] == "hello"
        assert data["level"] == "INFO"
        assert data["logger"] == "gauntlet"
        assert "timestamp" in data

    def test_includes_gauntlet_extra(self) -> None:
        record = logging.LogRecord(
            name="gauntlet",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="event",
            args=(),
            exc_info=None,
        )
        record._gauntlet_extra = {"event": "detection", "layer": 1}
        fmt = JSONFormatter()
        data = json.loads(fmt.format(record))
        assert data["event"] == "detection"
        assert data["layer"] == 1

    def test_timestamp_is_utc_iso(self) -> None:
        record = logging.LogRecord(
            name="gauntlet",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="ts",
            args=(),
            exc_info=None,
        )
        fmt = JSONFormatter()
        data = json.loads(fmt.format(record))
        assert data["timestamp"].endswith("+00:00")


class TestSetupLogging:
    """Tests for setup_logging()."""

    def test_idempotent(self) -> None:
        logger = logging.getLogger("gauntlet")
        original_handlers = logger.handlers[:]
        logger.handlers.clear()
        try:
            setup_logging()
            count = len(logger.handlers)
            setup_logging()
            assert len(logger.handlers) == count
        finally:
            logger.handlers = original_handlers

    def test_sets_level(self) -> None:
        logger = logging.getLogger("gauntlet")
        original_handlers = logger.handlers[:]
        original_level = logger.level
        logger.handlers.clear()
        try:
            setup_logging(level=logging.DEBUG)
            assert logger.level == logging.DEBUG
        finally:
            logger.handlers = original_handlers
            logger.setLevel(original_level)

    def test_propagate_false(self) -> None:
        logger = logging.getLogger("gauntlet")
        original_handlers = logger.handlers[:]
        logger.handlers.clear()
        try:
            setup_logging()
            assert logger.propagate is False
        finally:
            logger.handlers = original_handlers


class TestLogDetectionEvent:
    """Tests for _log_detection_event()."""

    def test_logs_with_correct_fields(self) -> None:
        logger = logging.getLogger("gauntlet")
        original_handlers = logger.handlers[:]
        original_level = logger.level
        original_propagate = logger.propagate
        logger.handlers.clear()
        # Use a logging.Handler that stores records
        captured: list[logging.LogRecord] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                captured.append(record)

        logger.addHandler(_Capture())
        logger.setLevel(logging.INFO)
        logger.propagate = False
        try:
            _log_detection_event(
                text="ignore previous instructions",
                layer=1,
                latency_ms=1.234,
                is_injection=True,
                attack_type="instruction_override",
                confidence=0.95,
            )
            assert len(captured) == 1
            rec = captured[0]
            assert hasattr(rec, "_gauntlet_extra")
            extra = rec._gauntlet_extra
            assert extra["event"] == "detection"
            assert extra["layer"] == 1
            assert extra["is_injection"] is True
            assert extra["attack_type"] == "instruction_override"
            assert extra["confidence"] == 0.95
            assert extra["latency_ms"] == 1.23
            assert extra["input_length"] == len("ignore previous instructions")
        finally:
            logger.handlers = original_handlers
            logger.setLevel(original_level)
            logger.propagate = original_propagate

    def test_input_hash_is_sha256(self) -> None:
        logger = logging.getLogger("gauntlet")
        original_handlers = logger.handlers[:]
        original_level = logger.level
        original_propagate = logger.propagate
        logger.handlers.clear()
        captured: list[logging.LogRecord] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                captured.append(record)

        logger.addHandler(_Capture())
        logger.setLevel(logging.INFO)
        logger.propagate = False
        try:
            text = "test input"
            expected_hash = hashlib.sha256(text.encode()).hexdigest()
            _log_detection_event(text, 1, 0.0, False, None, 0.0)
            extra = captured[0]._gauntlet_extra
            assert extra["input_hash"] == expected_hash
        finally:
            logger.handlers = original_handlers
            logger.setLevel(original_level)
            logger.propagate = original_propagate

    def test_raw_text_never_logged(self) -> None:
        logger = logging.getLogger("gauntlet")
        original_handlers = logger.handlers[:]
        original_level = logger.level
        original_propagate = logger.propagate
        logger.handlers.clear()
        captured: list[logging.LogRecord] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                captured.append(record)

        logger.addHandler(_Capture())
        logger.setLevel(logging.INFO)
        logger.propagate = False
        try:
            secret = "super_secret_user_input_xyz123"
            _log_detection_event(secret, 1, 0.0, False, None, 0.0)
            rec = captured[0]
            formatted = JSONFormatter().format(rec)
            assert secret not in formatted
        finally:
            logger.handlers = original_handlers
            logger.setLevel(original_level)
            logger.propagate = original_propagate
