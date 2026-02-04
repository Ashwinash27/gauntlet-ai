"""Tests for API key authentication."""

import pytest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.auth import (
    APIKeyInfo,
    generate_api_key,
    hash_api_key,
    validate_api_key_format,
    API_KEY_PREFIX,
)


class TestGenerateAPIKey:
    """Tests for API key generation."""

    def test_generates_key_with_correct_prefix(self):
        """Generated key should start with sk-argus-."""
        key = generate_api_key()
        assert key.startswith(API_KEY_PREFIX)

    def test_generates_key_with_correct_length(self):
        """Generated key should have correct total length."""
        key = generate_api_key()
        # sk-argus- (9 chars) + 32 random chars = 41 chars
        assert len(key) == 9 + 32

    def test_generates_unique_keys(self):
        """Should generate unique keys each time."""
        keys = [generate_api_key() for _ in range(100)]
        assert len(set(keys)) == 100


class TestHashAPIKey:
    """Tests for API key hashing."""

    def test_hashes_key_to_hex(self):
        """Should return a hex string."""
        key = "sk-argus-test123456789012345678901"
        hash_value = hash_api_key(key)
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_hash_is_deterministic(self):
        """Same key should produce same hash."""
        key = "sk-argus-test123456789012345678901"
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        assert hash1 == hash2

    def test_different_keys_produce_different_hashes(self):
        """Different keys should produce different hashes."""
        key1 = generate_api_key()
        key2 = generate_api_key()
        assert hash_api_key(key1) != hash_api_key(key2)

    def test_hash_is_sha256_length(self):
        """Hash should be 64 characters (SHA-256 hex)."""
        key = generate_api_key()
        hash_value = hash_api_key(key)
        assert len(hash_value) == 64


class TestValidateAPIKeyFormat:
    """Tests for API key format validation."""

    def test_valid_key_format(self):
        """Should accept valid key format."""
        key = generate_api_key()
        assert validate_api_key_format(key) is True

    def test_rejects_wrong_prefix(self):
        """Should reject keys with wrong prefix."""
        assert validate_api_key_format("sk-other-12345678901234567890123456789012") is False
        assert validate_api_key_format("api-key-12345678901234567890123456789012") is False

    def test_rejects_too_short(self):
        """Should reject keys that are too short."""
        assert validate_api_key_format("sk-argus-short") is False
        assert validate_api_key_format("sk-argus-") is False

    def test_rejects_empty_string(self):
        """Should reject empty string."""
        assert validate_api_key_format("") is False

    def test_accepts_keys_with_dashes_and_underscores(self):
        """Should accept keys with URL-safe characters."""
        # token_urlsafe can include - and _
        # The random part must be exactly 32 chars
        # sk-argus- is 9 chars, so random part starts at index 9
        key = "sk-argus-abcd_efgh-ijkl_mnopqrstuvwx12345"  # Exactly 32 chars
        assert len(key) == 9 + 32  # Verify length
        assert validate_api_key_format(key) is True


class TestAPIKeyInfo:
    """Tests for APIKeyInfo dataclass."""

    def test_api_key_info_creation(self):
        """Should create APIKeyInfo with all fields."""
        now = datetime.now(UTC)
        info = APIKeyInfo(
            id="test-id",
            name="Test Key",
            daily_limit=1000,
            is_active=True,
            created_at=now,
            last_used_at=None,
        )

        assert info.id == "test-id"
        assert info.name == "Test Key"
        assert info.daily_limit == 1000
        assert info.is_active is True
        assert info.created_at == now
        assert info.last_used_at is None

    def test_api_key_info_with_last_used(self):
        """Should handle last_used_at timestamp."""
        now = datetime.now(UTC)
        info = APIKeyInfo(
            id="test-id",
            name="Test Key",
            daily_limit=1000,
            is_active=True,
            created_at=now,
            last_used_at=now,
        )

        assert info.last_used_at == now


class TestValidateAPIKeyDependency:
    """Tests for the validate_api_key FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_rejects_missing_key_in_production(self):
        """Should reject requests without API key in production."""
        from fastapi import HTTPException
        from app.core.auth import validate_api_key

        mock_request = MagicMock()

        with patch("app.core.auth.get_settings") as mock_settings:
            mock_settings.return_value.is_production = True

            with pytest.raises(HTTPException) as exc_info:
                await validate_api_key(mock_request, api_key=None)

            assert exc_info.value.status_code == 401
            assert "Missing API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_allows_missing_key_in_development(self):
        """Should allow requests without API key in development."""
        from app.core.auth import validate_api_key

        mock_request = MagicMock()

        with patch("app.core.auth.get_settings") as mock_settings:
            mock_settings.return_value.is_production = False

            result = await validate_api_key(mock_request, api_key=None)

            assert result.id == "dev-key"
            assert result.name == "Development"

    @pytest.mark.asyncio
    async def test_rejects_invalid_format(self):
        """Should reject keys with invalid format."""
        from fastapi import HTTPException
        from app.core.auth import validate_api_key

        mock_request = MagicMock()

        with patch("app.core.auth.get_settings") as mock_settings:
            mock_settings.return_value.is_production = True

            with pytest.raises(HTTPException) as exc_info:
                await validate_api_key(mock_request, api_key="invalid-key")

            assert exc_info.value.status_code == 401
            assert "Invalid API key format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_rejects_key_not_found(self):
        """Should reject keys not found in database."""
        from fastapi import HTTPException
        from app.core.auth import validate_api_key

        mock_request = MagicMock()
        valid_key = generate_api_key()

        with patch("app.core.auth.get_settings") as mock_settings:
            mock_settings.return_value.is_production = True

            with patch("app.core.auth.get_api_key_info", return_value=None):
                with pytest.raises(HTTPException) as exc_info:
                    await validate_api_key(mock_request, api_key=valid_key)

                assert exc_info.value.status_code == 401
                assert "Invalid API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_accepts_valid_key(self):
        """Should accept valid API key."""
        from app.core.auth import validate_api_key

        mock_request = MagicMock()
        valid_key = generate_api_key()
        now = datetime.now(UTC)

        mock_key_info = APIKeyInfo(
            id="test-id",
            name="Test Key",
            daily_limit=1000,
            is_active=True,
            created_at=now,
            last_used_at=None,
        )

        with patch("app.core.auth.get_settings") as mock_settings:
            mock_settings.return_value.is_production = True

            with patch("app.core.auth.get_api_key_info", return_value=mock_key_info):
                with patch("app.core.auth.update_last_used"):
                    result = await validate_api_key(mock_request, api_key=valid_key)

                    assert result.id == "test-id"
                    assert result.name == "Test Key"
