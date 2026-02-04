"""Structured logging and cost tracking for Argus AI.

This module provides JSON structured logging using structlog,
plus cost tracking for API usage.
"""

import hashlib
import logging
import sys
from typing import Any

import structlog
from structlog.stdlib import BoundLogger

from app.core.config import get_settings

# API cost estimates (per 1K tokens)
COSTS_PER_1K_TOKENS = {
    "openai_embedding": 0.00002,  # $0.02 per 1M tokens
    "anthropic_haiku_input": 0.00025,  # $0.25 per 1M input tokens
    "anthropic_haiku_output": 0.00125,  # $1.25 per 1M output tokens
}

# Estimated tokens per request (rough averages)
ESTIMATED_TOKENS = {
    "embedding_request": 500,  # ~500 tokens per embedding
    "llm_input": 800,  # System prompt + prepared input
    "llm_output": 100,  # JSON response
}


def setup_logging() -> None:
    """
    Configure structured logging for the application.

    Sets up structlog with JSON rendering for production
    and pretty console output for development.
    """
    settings = get_settings()

    # Shared processors
    shared_processors: list[Any] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.is_production:
        # Production: JSON output
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: Pretty console output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )


def get_logger(name: str | None = None) -> BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name. If None, uses the calling module's name.

    Returns:
        Configured structlog BoundLogger instance.
    """
    return structlog.get_logger(name)


def hash_for_logging(value: str, length: int = 8) -> str:
    """
    Create a short hash of a value for logging without exposing raw data.

    Useful for logging API keys, user inputs, etc. without privacy concerns.

    Args:
        value: The value to hash.
        length: Length of the hash to return (default 8).

    Returns:
        Truncated SHA-256 hash of the value.
    """
    return hashlib.sha256(value.encode()).hexdigest()[:length]


def estimate_cost(layer: int, input_length: int = 0) -> dict[str, float]:
    """
    Estimate the API cost for a detection request.

    Args:
        layer: Which layer was reached (1, 2, or 3).
        input_length: Length of input text in characters.

    Returns:
        Dictionary with estimated costs by service.
    """
    costs = {}

    # Layer 2 uses OpenAI embeddings
    if layer >= 2:
        tokens = ESTIMATED_TOKENS["embedding_request"]
        costs["openai_embedding_usd"] = (
            tokens / 1000 * COSTS_PER_1K_TOKENS["openai_embedding"]
        )

    # Layer 3 uses Anthropic Claude
    if layer >= 3:
        input_tokens = ESTIMATED_TOKENS["llm_input"]
        output_tokens = ESTIMATED_TOKENS["llm_output"]
        costs["anthropic_input_usd"] = (
            input_tokens / 1000 * COSTS_PER_1K_TOKENS["anthropic_haiku_input"]
        )
        costs["anthropic_output_usd"] = (
            output_tokens / 1000 * COSTS_PER_1K_TOKENS["anthropic_haiku_output"]
        )

    costs["total_usd"] = sum(costs.values())
    return costs


class CostTracker:
    """
    Track API costs across requests.

    Thread-safe cost accumulator for monitoring API spend.
    """

    def __init__(self) -> None:
        """Initialize the cost tracker."""
        self._total_cost_usd: float = 0.0
        self._request_count: int = 0
        self._layer_counts: dict[int, int] = {1: 0, 2: 0, 3: 0}

    def record_request(self, layer_reached: int, cost_usd: float) -> None:
        """
        Record a detection request.

        Args:
            layer_reached: Highest layer that was executed.
            cost_usd: Estimated cost of the request.
        """
        self._total_cost_usd += cost_usd
        self._request_count += 1
        if layer_reached in self._layer_counts:
            self._layer_counts[layer_reached] += 1

    @property
    def total_cost_usd(self) -> float:
        """Get total accumulated cost."""
        return self._total_cost_usd

    @property
    def request_count(self) -> int:
        """Get total request count."""
        return self._request_count

    def get_stats(self) -> dict[str, Any]:
        """
        Get cost tracking statistics.

        Returns:
            Dictionary with cost and request statistics.
        """
        return {
            "total_cost_usd": round(self._total_cost_usd, 6),
            "request_count": self._request_count,
            "avg_cost_per_request_usd": (
                round(self._total_cost_usd / self._request_count, 6)
                if self._request_count > 0
                else 0.0
            ),
            "layer_distribution": self._layer_counts.copy(),
        }


# Global cost tracker instance
cost_tracker = CostTracker()


def log_detection_request(
    logger: BoundLogger,
    is_injection: bool,
    layer_reached: int,
    attack_type: str | None,
    latency_ms: float,
    input_length: int,
    api_key_hash: str | None = None,
) -> None:
    """
    Log a detection request with standard fields.

    Args:
        logger: Structlog logger instance.
        is_injection: Whether injection was detected.
        layer_reached: Highest layer executed.
        attack_type: Type of attack detected (if any).
        latency_ms: Total processing time.
        input_length: Length of input text.
        api_key_hash: Hashed API key (optional).
    """
    cost = estimate_cost(layer_reached, input_length)
    cost_tracker.record_request(layer_reached, cost["total_usd"])

    logger.info(
        "detection_complete",
        is_injection=is_injection,
        layer_reached=layer_reached,
        attack_type=attack_type,
        latency_ms=round(latency_ms, 2),
        input_length=input_length,
        estimated_cost_usd=cost["total_usd"],
        api_key_hash=api_key_hash,
    )


def log_rate_limit_exceeded(
    logger: BoundLogger,
    api_key_hash: str,
    limit: int,
    current: int,
) -> None:
    """Log a rate limit exceeded event."""
    logger.warning(
        "rate_limit_exceeded",
        api_key_hash=api_key_hash,
        limit=limit,
        current=current,
    )


def log_auth_failed(
    logger: BoundLogger,
    reason: str,
    api_key_hash: str | None = None,
) -> None:
    """Log an authentication failure."""
    logger.warning(
        "auth_failed",
        reason=reason,
        api_key_hash=api_key_hash,
    )


def log_layer3_error(
    logger: BoundLogger,
    error: str,
    is_timeout: bool = False,
) -> None:
    """Log a Layer 3 (LLM) error."""
    event = "layer3_timeout" if is_timeout else "layer3_error"
    logger.warning(
        event,
        error=error,
        is_timeout=is_timeout,
    )


__all__ = [
    "setup_logging",
    "get_logger",
    "hash_for_logging",
    "estimate_cost",
    "CostTracker",
    "cost_tracker",
    "log_detection_request",
    "log_rate_limit_exceeded",
    "log_auth_failed",
    "log_layer3_error",
]
