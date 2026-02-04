"""Tests for rate limiting."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.auth import APIKeyInfo
from app.core.rate_limiter import (
    RateLimitStatus,
    check_rate_limit,
    enforce_rate_limit,
    add_rate_limit_headers,
    get_day_start_utc,
    get_day_end_utc,
)


@pytest.fixture
def mock_api_key_info():
    """Create a mock APIKeyInfo."""
    return APIKeyInfo(
        id="test-key-id",
        name="Test Key",
        daily_limit=1000,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        last_used_at=None,
    )


class TestRateLimitStatus:
    """Tests for RateLimitStatus dataclass."""

    def test_status_creation(self):
        """Should create RateLimitStatus with all fields."""
        reset_at = datetime.now(timezone.utc)
        status = RateLimitStatus(
            limit=1000,
            remaining=500,
            reset_at=reset_at,
            is_exceeded=False,
        )

        assert status.limit == 1000
        assert status.remaining == 500
        assert status.reset_at == reset_at
        assert status.is_exceeded is False

    def test_exceeded_status(self):
        """Should correctly indicate exceeded status."""
        status = RateLimitStatus(
            limit=1000,
            remaining=0,
            reset_at=datetime.now(timezone.utc),
            is_exceeded=True,
        )

        assert status.is_exceeded is True
        assert status.remaining == 0


class TestDayBoundaries:
    """Tests for UTC day boundary functions."""

    def test_day_start_is_midnight(self):
        """Day start should be at midnight UTC."""
        start = get_day_start_utc()

        assert start.hour == 0
        assert start.minute == 0
        assert start.second == 0
        assert start.microsecond == 0

    def test_day_end_is_end_of_day(self):
        """Day end should be at 23:59:59 UTC."""
        end = get_day_end_utc()

        assert end.hour == 23
        assert end.minute == 59
        assert end.second == 59

    def test_day_start_and_end_same_day(self):
        """Day start and end should be on the same day."""
        start = get_day_start_utc()
        end = get_day_end_utc()

        assert start.date() == end.date()


class TestCheckRateLimit:
    """Tests for check_rate_limit function."""

    @pytest.mark.asyncio
    async def test_returns_correct_limit(self, mock_api_key_info):
        """Should return the API key's daily limit."""
        mock_request = MagicMock()

        with patch("app.core.rate_limiter.get_request_count_today", return_value=100):
            status = await check_rate_limit(mock_request, mock_api_key_info)

        assert status.limit == 1000

    @pytest.mark.asyncio
    async def test_calculates_remaining(self, mock_api_key_info):
        """Should calculate remaining requests correctly."""
        mock_request = MagicMock()

        with patch("app.core.rate_limiter.get_request_count_today", return_value=100):
            status = await check_rate_limit(mock_request, mock_api_key_info)

        assert status.remaining == 900  # 1000 - 100

    @pytest.mark.asyncio
    async def test_remaining_never_negative(self, mock_api_key_info):
        """Remaining should not be negative."""
        mock_request = MagicMock()

        with patch("app.core.rate_limiter.get_request_count_today", return_value=1500):
            status = await check_rate_limit(mock_request, mock_api_key_info)

        assert status.remaining == 0
        assert status.is_exceeded is True

    @pytest.mark.asyncio
    async def test_exceeded_when_at_limit(self, mock_api_key_info):
        """Should be exceeded when at exact limit."""
        mock_request = MagicMock()

        with patch("app.core.rate_limiter.get_request_count_today", return_value=1000):
            status = await check_rate_limit(mock_request, mock_api_key_info)

        assert status.remaining == 0
        assert status.is_exceeded is True

    @pytest.mark.asyncio
    async def test_not_exceeded_when_under_limit(self, mock_api_key_info):
        """Should not be exceeded when under limit."""
        mock_request = MagicMock()

        with patch("app.core.rate_limiter.get_request_count_today", return_value=999):
            status = await check_rate_limit(mock_request, mock_api_key_info)

        assert status.remaining == 1
        assert status.is_exceeded is False


class TestEnforceRateLimit:
    """Tests for enforce_rate_limit function."""

    @pytest.mark.asyncio
    async def test_allows_under_limit(self, mock_api_key_info):
        """Should not raise exception when under limit."""
        mock_request = MagicMock()

        with patch("app.core.rate_limiter.get_request_count_today", return_value=100):
            status = await enforce_rate_limit(mock_request, mock_api_key_info)

        assert status.is_exceeded is False

    @pytest.mark.asyncio
    async def test_raises_429_when_exceeded(self, mock_api_key_info):
        """Should raise 429 HTTPException when limit exceeded."""
        from fastapi import HTTPException

        mock_request = MagicMock()

        with patch("app.core.rate_limiter.get_request_count_today", return_value=1000):
            with pytest.raises(HTTPException) as exc_info:
                await enforce_rate_limit(mock_request, mock_api_key_info)

        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_429_includes_headers(self, mock_api_key_info):
        """429 response should include rate limit headers."""
        from fastapi import HTTPException

        mock_request = MagicMock()

        with patch("app.core.rate_limiter.get_request_count_today", return_value=1000):
            with pytest.raises(HTTPException) as exc_info:
                await enforce_rate_limit(mock_request, mock_api_key_info)

        headers = exc_info.value.headers
        assert "X-RateLimit-Limit" in headers
        assert "X-RateLimit-Remaining" in headers
        assert "X-RateLimit-Reset" in headers
        assert "Retry-After" in headers


class TestAddRateLimitHeaders:
    """Tests for add_rate_limit_headers function."""

    def test_adds_all_headers(self):
        """Should add all rate limit headers."""
        mock_response = MagicMock()
        mock_response.headers = {}

        status = RateLimitStatus(
            limit=1000,
            remaining=500,
            reset_at=datetime(2024, 1, 15, 23, 59, 59, tzinfo=timezone.utc),
            is_exceeded=False,
        )

        add_rate_limit_headers(mock_response, status)

        assert mock_response.headers["X-RateLimit-Limit"] == "1000"
        assert mock_response.headers["X-RateLimit-Remaining"] == "500"
        assert "X-RateLimit-Reset" in mock_response.headers

    def test_reset_is_timestamp(self):
        """Reset header should be a Unix timestamp."""
        mock_response = MagicMock()
        mock_response.headers = {}

        reset_time = datetime(2024, 1, 15, 23, 59, 59, tzinfo=timezone.utc)
        status = RateLimitStatus(
            limit=1000,
            remaining=500,
            reset_at=reset_time,
            is_exceeded=False,
        )

        add_rate_limit_headers(mock_response, status)

        reset_value = int(mock_response.headers["X-RateLimit-Reset"])
        assert reset_value == int(reset_time.timestamp())


class TestRequestCounting:
    """Tests for request counting."""

    @pytest.mark.asyncio
    async def test_count_returns_zero_when_no_supabase(self):
        """Should return 0 when Supabase client is not available."""
        from app.core.rate_limiter import get_request_count_today

        mock_request = MagicMock()

        with patch("app.main.app_state") as mock_state:
            mock_state.supabase_client = None

            count = await get_request_count_today(mock_request, "test-id")

        assert count == 0

    @pytest.mark.asyncio
    async def test_count_returns_zero_on_error(self):
        """Should return 0 on database error."""
        from app.core.rate_limiter import get_request_count_today

        mock_request = MagicMock()
        mock_supabase = AsyncMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.side_effect = Exception("DB Error")

        with patch("app.main.app_state") as mock_state:
            mock_state.supabase_client = mock_supabase

            count = await get_request_count_today(mock_request, "test-id")

        assert count == 0
