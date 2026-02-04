"""API key authentication for Argus AI.

This module provides simple API key validation using SHA-256 hashing.
API keys are stored as hashes in Supabase; the raw key is never stored.
"""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from app.core.config import get_settings
from app.core.logging import get_logger, hash_for_logging, log_auth_failed

logger = get_logger(__name__)

# API key header name
API_KEY_HEADER = "X-API-Key"

# API key format: sk-argus-{32 random chars}
API_KEY_PREFIX = "sk-argus-"


@dataclass
class APIKeyInfo:
    """Information about a validated API key."""

    id: str
    name: str
    daily_limit: int
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None


def generate_api_key() -> str:
    """
    Generate a new API key.

    Returns:
        New API key in format: sk-argus-{32 random alphanumeric chars}
    """
    random_part = secrets.token_urlsafe(24)[:32]  # 32 chars
    return f"{API_KEY_PREFIX}{random_part}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for storage.

    Uses SHA-256 to create a one-way hash of the key.

    Args:
        api_key: The raw API key to hash.

    Returns:
        SHA-256 hex digest of the key.
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def validate_api_key_format(api_key: str) -> bool:
    """
    Validate that an API key has the correct format.

    Args:
        api_key: The API key to validate.

    Returns:
        True if format is valid, False otherwise.
    """
    if not api_key.startswith(API_KEY_PREFIX):
        return False
    random_part = api_key[len(API_KEY_PREFIX) :]
    return len(random_part) == 32 and random_part.replace("-", "").replace("_", "").isalnum()


# FastAPI security scheme
api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


async def get_api_key_info(
    request: Request,
    api_key: str,
) -> APIKeyInfo | None:
    """
    Look up API key information from Supabase.

    Args:
        request: FastAPI request for accessing app state.
        api_key: The raw API key to look up.

    Returns:
        APIKeyInfo if found and active, None otherwise.
    """
    from app.main import app_state

    if app_state.supabase_client is None:
        logger.warning("Supabase client not available for auth")
        return None

    key_hash = hash_api_key(api_key)

    try:
        result = await app_state.supabase_client.table("api_keys").select(
            "id, name, daily_limit, is_active, created_at, last_used_at"
        ).eq("key_hash", key_hash).eq("is_active", True).execute()

        if not result.data:
            return None

        row = result.data[0]
        return APIKeyInfo(
            id=row["id"],
            name=row["name"],
            daily_limit=row["daily_limit"],
            is_active=row["is_active"],
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
            last_used_at=(
                datetime.fromisoformat(row["last_used_at"].replace("Z", "+00:00"))
                if row.get("last_used_at")
                else None
            ),
        )
    except Exception as e:
        logger.error(f"Error looking up API key: {e}")
        return None


async def update_last_used(request: Request, key_id: str) -> None:
    """
    Update the last_used_at timestamp for an API key.

    Args:
        request: FastAPI request for accessing app state.
        key_id: The API key ID to update.
    """
    from app.main import app_state

    if app_state.supabase_client is None:
        return

    try:
        await app_state.supabase_client.table("api_keys").update(
            {"last_used_at": datetime.now(UTC).isoformat()}
        ).eq("id", key_id).execute()
    except Exception as e:
        logger.warning(f"Failed to update last_used_at: {e}")


async def validate_api_key(
    request: Request,
    api_key: str | None = Security(api_key_header),
) -> APIKeyInfo:
    """
    Validate the API key from request header.

    This is a FastAPI dependency that validates the X-API-Key header.

    Args:
        request: FastAPI request object.
        api_key: API key from header (injected by FastAPI).

    Returns:
        APIKeyInfo for the validated key.

    Raises:
        HTTPException: If key is missing, invalid format, or not found.
    """
    settings = get_settings()

    # Check if auth is enabled (can be disabled for development)
    if not settings.is_production and not api_key:
        # Return a dummy key info for development
        return APIKeyInfo(
            id="dev-key",
            name="Development",
            daily_limit=999999,
            is_active=True,
            created_at=datetime.now(UTC),
            last_used_at=None,
        )

    if not api_key:
        log_auth_failed(logger, "missing_api_key")
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not validate_api_key_format(api_key):
        log_auth_failed(logger, "invalid_format", hash_for_logging(api_key))
        raise HTTPException(
            status_code=401,
            detail="Invalid API key format.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    key_info = await get_api_key_info(request, api_key)

    if key_info is None:
        log_auth_failed(logger, "not_found", hash_for_logging(api_key))
        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Update last used timestamp (fire and forget)
    await update_last_used(request, key_info.id)

    return key_info


# Type alias for dependency injection
APIKeyDep = Annotated[APIKeyInfo, Depends(validate_api_key)]


__all__ = [
    "APIKeyInfo",
    "APIKeyDep",
    "generate_api_key",
    "hash_api_key",
    "validate_api_key",
    "validate_api_key_format",
    "API_KEY_HEADER",
    "API_KEY_PREFIX",
]
