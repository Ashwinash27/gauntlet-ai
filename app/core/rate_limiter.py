"""Rate limiting for Argus AI API.

This module provides rate limiting based on daily request counts
tracked in Supabase. Each API key has a configurable daily limit.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, Request, Response

from app.core.auth import APIKeyInfo
from app.core.config import get_settings
from app.core.logging import get_logger, hash_for_logging, log_rate_limit_exceeded

logger = get_logger(__name__)


@dataclass
class RateLimitStatus:
    """Current rate limit status for an API key."""

    limit: int
    remaining: int
    reset_at: datetime
    is_exceeded: bool


def get_day_start_utc() -> datetime:
    """Get the start of the current UTC day."""
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def get_day_end_utc() -> datetime:
    """Get the end of the current UTC day."""
    start = get_day_start_utc()
    return start.replace(hour=23, minute=59, second=59, microsecond=999999)


async def get_request_count_today(
    request: Request,
    api_key_id: str,
) -> int:
    """
    Get the number of requests made today for an API key.

    Args:
        request: FastAPI request for accessing app state.
        api_key_id: The API key ID to check.

    Returns:
        Number of requests made today, or 0 on error.
    """
    from app.main import app_state

    if app_state.supabase_client is None:
        return 0

    day_start = get_day_start_utc().isoformat()

    try:
        result = await app_state.supabase_client.table("request_logs").select(
            "id", count="exact"
        ).eq("api_key_id", api_key_id).gte("created_at", day_start).execute()

        return result.count or 0
    except Exception as e:
        logger.warning(f"Failed to get request count: {e}")
        return 0


async def log_request(
    request: Request,
    api_key_id: str,
    is_injection: bool,
    layer_reached: int,
    latency_ms: float,
) -> None:
    """
    Log a detection request for rate limiting and analytics.

    Args:
        request: FastAPI request for accessing app state.
        api_key_id: The API key ID making the request.
        is_injection: Whether an injection was detected.
        layer_reached: Highest layer that was executed.
        latency_ms: Total processing time.
    """
    from app.main import app_state

    if app_state.supabase_client is None:
        return

    try:
        await app_state.supabase_client.table("request_logs").insert({
            "api_key_id": api_key_id,
            "is_injection": is_injection,
            "layer_reached": layer_reached,
            "latency_ms": latency_ms,
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to log request: {e}")


async def check_rate_limit(
    request: Request,
    api_key_info: APIKeyInfo,
) -> RateLimitStatus:
    """
    Check if the API key has exceeded its rate limit.

    Args:
        request: FastAPI request for accessing app state.
        api_key_info: The validated API key info.

    Returns:
        RateLimitStatus with current limit status.
    """
    settings = get_settings()

    # Use key's daily limit or default
    limit = api_key_info.daily_limit or settings.default_rate_limit

    # Get current count
    current_count = await get_request_count_today(request, api_key_info.id)
    remaining = max(0, limit - current_count)
    reset_at = get_day_end_utc()

    return RateLimitStatus(
        limit=limit,
        remaining=remaining,
        reset_at=reset_at,
        is_exceeded=remaining == 0,
    )


def add_rate_limit_headers(response: Response, status: RateLimitStatus) -> None:
    """
    Add rate limit headers to a response.

    Args:
        response: FastAPI response to add headers to.
        status: Current rate limit status.
    """
    response.headers["X-RateLimit-Limit"] = str(status.limit)
    response.headers["X-RateLimit-Remaining"] = str(status.remaining)
    response.headers["X-RateLimit-Reset"] = str(int(status.reset_at.timestamp()))


async def enforce_rate_limit(
    request: Request,
    api_key_info: APIKeyInfo,
) -> RateLimitStatus:
    """
    Check rate limit and raise exception if exceeded.

    This is meant to be called as part of request processing.

    Args:
        request: FastAPI request for accessing app state.
        api_key_info: The validated API key info.

    Returns:
        RateLimitStatus for adding headers to response.

    Raises:
        HTTPException: If rate limit is exceeded (429).
    """
    status = await check_rate_limit(request, api_key_info)

    if status.is_exceeded:
        log_rate_limit_exceeded(
            logger,
            hash_for_logging(api_key_info.id),
            status.limit,
            status.limit - status.remaining,
        )
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit": status.limit,
                "reset_at": status.reset_at.isoformat(),
            },
            headers={
                "X-RateLimit-Limit": str(status.limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(status.reset_at.timestamp())),
                "Retry-After": str(int((status.reset_at - datetime.now(timezone.utc)).total_seconds())),
            },
        )

    return status


__all__ = [
    "RateLimitStatus",
    "check_rate_limit",
    "enforce_rate_limit",
    "add_rate_limit_headers",
    "log_request",
    "get_request_count_today",
]
