"""Client factories for external services.

Provides async client instances for OpenAI, Supabase, and Anthropic with proper
configuration from environment variables.
"""

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from supabase import acreate_client, AsyncClient

from app.core.config import get_settings


async def get_openai_client() -> AsyncOpenAI:
    """
    Create an async OpenAI client.

    Returns:
        Configured AsyncOpenAI client instance.

    Raises:
        ValueError: If OPENAI_API_KEY is not configured.
    """
    settings = get_settings()
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured")
    return AsyncOpenAI(api_key=settings.openai_api_key)


async def get_supabase_client() -> AsyncClient:
    """
    Create an async Supabase client.

    Returns:
        Configured AsyncClient instance.

    Raises:
        ValueError: If Supabase credentials are not configured.
    """
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be configured")
    return await acreate_client(settings.supabase_url, settings.supabase_key)


async def get_anthropic_client() -> AsyncAnthropic:
    """
    Create an async Anthropic client for Claude API.

    Returns:
        Configured AsyncAnthropic client instance.

    Raises:
        ValueError: If ANTHROPIC_API_KEY is not configured.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY is not configured")
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


__all__ = ["get_openai_client", "get_supabase_client", "get_anthropic_client"]
