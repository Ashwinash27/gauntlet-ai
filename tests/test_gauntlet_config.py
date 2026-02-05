"""Tests for Gauntlet configuration management."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from gauntlet.config import (
    _parse_toml,
    _write_toml,
    get_config_value,
    list_config,
    load_config,
    set_config_value,
)
from gauntlet.exceptions import ConfigError


# ---------------------------------------------------------------------------
# Tests: TOML parsing
# ---------------------------------------------------------------------------

class TestParseToml:
    """Tests for the minimal TOML parser."""

    def test_parses_quoted_values(self) -> None:
        """Should parse key = \"value\" format."""
        text = 'openai_key = "sk-test-key-123"'
        result = _parse_toml(text)
        assert result == {"openai_key": "sk-test-key-123"}

    def test_parses_single_quoted_values(self) -> None:
        """Should parse key = 'value' format."""
        text = "openai_key = 'sk-test-key-123'"
        result = _parse_toml(text)
        assert result == {"openai_key": "sk-test-key-123"}

    def test_parses_unquoted_values(self) -> None:
        """Should parse key = value format (no quotes)."""
        text = "embedding_threshold = 0.55"
        result = _parse_toml(text)
        assert result == {"embedding_threshold": "0.55"}

    def test_parses_multiple_lines(self) -> None:
        """Should parse multiple key-value pairs."""
        text = 'openai_key = "sk-123"\nanthropic_key = "sk-ant-456"'
        result = _parse_toml(text)
        assert result == {
            "openai_key": "sk-123",
            "anthropic_key": "sk-ant-456",
        }

    def test_ignores_comments(self) -> None:
        """Should skip comment lines."""
        text = '# This is a comment\nopenai_key = "sk-123"\n# Another comment'
        result = _parse_toml(text)
        assert result == {"openai_key": "sk-123"}

    def test_ignores_section_headers(self) -> None:
        """Should skip TOML section headers."""
        text = '[section]\nopenai_key = "sk-123"'
        result = _parse_toml(text)
        assert result == {"openai_key": "sk-123"}

    def test_ignores_blank_lines(self) -> None:
        """Should skip blank lines."""
        text = '\n\nopenai_key = "sk-123"\n\n'
        result = _parse_toml(text)
        assert result == {"openai_key": "sk-123"}

    def test_ignores_lines_without_equals(self) -> None:
        """Should skip lines without = sign."""
        text = 'this has no equals sign\nopenai_key = "sk-123"'
        result = _parse_toml(text)
        assert result == {"openai_key": "sk-123"}

    def test_strips_whitespace(self) -> None:
        """Should strip whitespace around key and value."""
        text = '  openai_key   =   "sk-123"  '
        result = _parse_toml(text)
        assert result == {"openai_key": "sk-123"}

    def test_empty_string(self) -> None:
        """Should return empty dict for empty string."""
        result = _parse_toml("")
        assert result == {}

    def test_value_with_equals_sign(self) -> None:
        """Should handle values that contain = sign."""
        text = 'key = "value=with=equals"'
        result = _parse_toml(text)
        assert result == {"key": "value=with=equals"}


# ---------------------------------------------------------------------------
# Tests: set_config_value / get_config_value
# ---------------------------------------------------------------------------

class TestSetGetConfig:
    """Tests for set_config_value and get_config_value."""

    def test_set_and_get_value(self, tmp_path: Path) -> None:
        """Should write and read back a config value."""
        config_file = tmp_path / "config.toml"
        config_dir = tmp_path

        with patch("gauntlet.config._CONFIG_FILE", config_file), \
             patch("gauntlet.config._CONFIG_DIR", config_dir):
            set_config_value("openai_key", "sk-test-12345")
            value = get_config_value("openai_key")
            assert value == "sk-test-12345"

    def test_set_overwrites_existing(self, tmp_path: Path) -> None:
        """Should overwrite existing value."""
        config_file = tmp_path / "config.toml"
        config_dir = tmp_path

        with patch("gauntlet.config._CONFIG_FILE", config_file), \
             patch("gauntlet.config._CONFIG_DIR", config_dir):
            set_config_value("openai_key", "sk-old")
            set_config_value("openai_key", "sk-new")
            value = get_config_value("openai_key")
            assert value == "sk-new"

    def test_set_multiple_keys(self, tmp_path: Path) -> None:
        """Should support setting multiple different keys."""
        config_file = tmp_path / "config.toml"
        config_dir = tmp_path

        with patch("gauntlet.config._CONFIG_FILE", config_file), \
             patch("gauntlet.config._CONFIG_DIR", config_dir):
            set_config_value("openai_key", "sk-openai")
            set_config_value("anthropic_key", "sk-ant-anthropic")

            assert get_config_value("openai_key") == "sk-openai"
            assert get_config_value("anthropic_key") == "sk-ant-anthropic"

    def test_get_nonexistent_key_returns_none(self, tmp_path: Path) -> None:
        """Should return None for keys not in config or env."""
        config_file = tmp_path / "config.toml"
        config_dir = tmp_path

        with patch("gauntlet.config._CONFIG_FILE", config_file), \
             patch("gauntlet.config._CONFIG_DIR", config_dir), \
             patch.dict(os.environ, {}, clear=True):
            # Remove any real env vars
            env = os.environ.copy()
            for k in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
                env.pop(k, None)
            with patch.dict(os.environ, env, clear=True):
                value = get_config_value("openai_key")
                assert value is None


# ---------------------------------------------------------------------------
# Tests: Env var fallback
# ---------------------------------------------------------------------------

class TestEnvVarFallback:
    """Tests for environment variable fallback."""

    def test_falls_back_to_env_var(self, tmp_path: Path) -> None:
        """Should fall back to env var when config file has no entry."""
        config_file = tmp_path / "config.toml"
        config_dir = tmp_path

        with patch("gauntlet.config._CONFIG_FILE", config_file), \
             patch("gauntlet.config._CONFIG_DIR", config_dir), \
             patch.dict(os.environ, {"OPENAI_API_KEY": "sk-from-env"}):
            value = get_config_value("openai_key")
            assert value == "sk-from-env"

    def test_config_file_takes_priority_over_env(self, tmp_path: Path) -> None:
        """Config file value should take priority over env var."""
        config_file = tmp_path / "config.toml"
        config_dir = tmp_path

        with patch("gauntlet.config._CONFIG_FILE", config_file), \
             patch("gauntlet.config._CONFIG_DIR", config_dir), \
             patch.dict(os.environ, {"OPENAI_API_KEY": "sk-env-value"}):
            set_config_value("openai_key", "sk-file-value")
            value = get_config_value("openai_key")
            assert value == "sk-file-value"

    def test_anthropic_env_fallback(self, tmp_path: Path) -> None:
        """Should resolve anthropic key from env var."""
        config_file = tmp_path / "config.toml"
        config_dir = tmp_path

        with patch("gauntlet.config._CONFIG_FILE", config_file), \
             patch("gauntlet.config._CONFIG_DIR", config_dir), \
             patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-from-env"}):
            value = get_config_value("anthropic_key")
            assert value == "sk-ant-from-env"


# ---------------------------------------------------------------------------
# Tests: list_config
# ---------------------------------------------------------------------------

class TestListConfig:
    """Tests for list_config."""

    def test_lists_all_keys(self, tmp_path: Path) -> None:
        """Should list all valid config keys."""
        config_file = tmp_path / "config.toml"
        config_dir = tmp_path

        with patch("gauntlet.config._CONFIG_FILE", config_file), \
             patch("gauntlet.config._CONFIG_DIR", config_dir), \
             patch.dict(os.environ, {}, clear=True):
            env = os.environ.copy()
            for k in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                       "GAUNTLET_EMBEDDING_MODEL", "GAUNTLET_EMBEDDING_THRESHOLD",
                       "GAUNTLET_LLM_MODEL", "GAUNTLET_LLM_TIMEOUT"]:
                env.pop(k, None)
            with patch.dict(os.environ, env, clear=True):
                result = list_config()
                expected_keys = {
                    "openai_key", "anthropic_key", "embedding_model",
                    "embedding_threshold", "llm_model", "llm_timeout",
                }
                assert set(result.keys()) == expected_keys

    def test_shows_config_file_source(self, tmp_path: Path) -> None:
        """Should indicate 'config file' as source."""
        config_file = tmp_path / "config.toml"
        config_dir = tmp_path

        with patch("gauntlet.config._CONFIG_FILE", config_file), \
             patch("gauntlet.config._CONFIG_DIR", config_dir):
            set_config_value("embedding_model", "text-embedding-3-large")
            result = list_config()
            assert "config file" in result["embedding_model"]

    def test_shows_env_source(self, tmp_path: Path) -> None:
        """Should indicate env var name as source."""
        config_file = tmp_path / "config.toml"
        config_dir = tmp_path

        with patch("gauntlet.config._CONFIG_FILE", config_file), \
             patch("gauntlet.config._CONFIG_DIR", config_dir), \
             patch.dict(os.environ, {"GAUNTLET_LLM_MODEL": "claude-3-sonnet-20240229"}):
            result = list_config()
            assert "env: GAUNTLET_LLM_MODEL" in result["llm_model"]

    def test_unset_keys_are_none(self, tmp_path: Path) -> None:
        """Should return None for unset keys."""
        config_file = tmp_path / "config.toml"
        config_dir = tmp_path

        with patch("gauntlet.config._CONFIG_FILE", config_file), \
             patch("gauntlet.config._CONFIG_DIR", config_dir), \
             patch.dict(os.environ, {}, clear=True):
            env = os.environ.copy()
            for k in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                       "GAUNTLET_EMBEDDING_MODEL", "GAUNTLET_EMBEDDING_THRESHOLD",
                       "GAUNTLET_LLM_MODEL", "GAUNTLET_LLM_TIMEOUT"]:
                env.pop(k, None)
            with patch.dict(os.environ, env, clear=True):
                result = list_config()
                # All values should be None
                for value in result.values():
                    assert value is None


# ---------------------------------------------------------------------------
# Tests: Key masking
# ---------------------------------------------------------------------------

class TestKeyMasking:
    """Tests for sensitive key masking in list_config."""

    def test_masks_long_api_key_in_config(self, tmp_path: Path) -> None:
        """Should mask API keys (show first 8 and last 4 chars)."""
        config_file = tmp_path / "config.toml"
        config_dir = tmp_path

        with patch("gauntlet.config._CONFIG_FILE", config_file), \
             patch("gauntlet.config._CONFIG_DIR", config_dir):
            set_config_value("openai_key", "sk-abcdefghijklmnopqrstuvwxyz")
            result = list_config()
            value = result["openai_key"]
            assert "sk-abcde" in value  # first 8 chars
            assert "wxyz" in value  # last 4 chars
            assert "..." in value  # masking indicator
            assert "config file" in value

    def test_masks_short_api_key(self, tmp_path: Path) -> None:
        """Should fully mask short keys."""
        config_file = tmp_path / "config.toml"
        config_dir = tmp_path

        with patch("gauntlet.config._CONFIG_FILE", config_file), \
             patch("gauntlet.config._CONFIG_DIR", config_dir):
            set_config_value("openai_key", "short")
            result = list_config()
            value = result["openai_key"]
            assert "***" in value

    def test_masks_env_api_key(self, tmp_path: Path) -> None:
        """Should mask keys coming from env vars."""
        config_file = tmp_path / "config.toml"
        config_dir = tmp_path

        with patch("gauntlet.config._CONFIG_FILE", config_file), \
             patch("gauntlet.config._CONFIG_DIR", config_dir), \
             patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-long-secret-key-value-here"}):
            result = list_config()
            value = result["anthropic_key"]
            assert "..." in value
            assert "env: ANTHROPIC_API_KEY" in value

    def test_non_key_values_not_masked(self, tmp_path: Path) -> None:
        """Should not mask non-key config values."""
        config_file = tmp_path / "config.toml"
        config_dir = tmp_path

        with patch("gauntlet.config._CONFIG_FILE", config_file), \
             patch("gauntlet.config._CONFIG_DIR", config_dir):
            set_config_value("embedding_model", "text-embedding-3-small")
            result = list_config()
            value = result["embedding_model"]
            assert "text-embedding-3-small" in value
            assert "..." not in value


# ---------------------------------------------------------------------------
# Tests: Invalid key handling
# ---------------------------------------------------------------------------

class TestInvalidKeyHandling:
    """Tests for handling invalid config keys."""

    def test_set_invalid_key_raises_error(self, tmp_path: Path) -> None:
        """Should raise ConfigError for unknown keys."""
        config_file = tmp_path / "config.toml"
        config_dir = tmp_path

        with patch("gauntlet.config._CONFIG_FILE", config_file), \
             patch("gauntlet.config._CONFIG_DIR", config_dir):
            with pytest.raises(ConfigError, match="Unknown config key"):
                set_config_value("totally_invalid_key", "some-value")

    def test_set_invalid_key_message_lists_valid_keys(self, tmp_path: Path) -> None:
        """Error message should list valid keys."""
        config_file = tmp_path / "config.toml"
        config_dir = tmp_path

        with patch("gauntlet.config._CONFIG_FILE", config_file), \
             patch("gauntlet.config._CONFIG_DIR", config_dir):
            with pytest.raises(ConfigError) as exc_info:
                set_config_value("bad_key", "value")
            error_msg = str(exc_info.value)
            assert "openai_key" in error_msg
            assert "anthropic_key" in error_msg

    def test_get_unknown_key_returns_none(self, tmp_path: Path) -> None:
        """get_config_value with unknown key should return None (no crash)."""
        config_file = tmp_path / "config.toml"
        config_dir = tmp_path

        with patch("gauntlet.config._CONFIG_FILE", config_file), \
             patch("gauntlet.config._CONFIG_DIR", config_dir):
            # Unknown key is not in _KEY_MAP, so no env fallback
            value = get_config_value("nonexistent_key")
            assert value is None


# ---------------------------------------------------------------------------
# Tests: load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:
    """Tests for load_config."""

    def test_returns_empty_dict_when_no_file(self, tmp_path: Path) -> None:
        """Should return empty dict when config file doesn't exist."""
        config_file = tmp_path / "nonexistent.toml"

        with patch("gauntlet.config._CONFIG_FILE", config_file):
            result = load_config()
            assert result == {}

    def test_reads_existing_file(self, tmp_path: Path) -> None:
        """Should read existing config file."""
        config_file = tmp_path / "config.toml"
        config_file.write_text('openai_key = "sk-test-value"\n')

        with patch("gauntlet.config._CONFIG_FILE", config_file):
            result = load_config()
            assert result == {"openai_key": "sk-test-value"}


# ---------------------------------------------------------------------------
# Tests: _write_toml
# ---------------------------------------------------------------------------

class TestWriteToml:
    """Tests for the TOML writer."""

    def test_creates_config_dir(self, tmp_path: Path) -> None:
        """Should create config directory if it doesn't exist."""
        config_dir = tmp_path / "new_dir"
        config_file = config_dir / "config.toml"

        with patch("gauntlet.config._CONFIG_DIR", config_dir), \
             patch("gauntlet.config._CONFIG_FILE", config_file):
            _write_toml({"openai_key": "sk-test"})
            assert config_dir.exists()
            assert config_file.exists()

    def test_writes_valid_toml(self, tmp_path: Path) -> None:
        """Written file should be parseable."""
        config_file = tmp_path / "config.toml"
        config_dir = tmp_path

        with patch("gauntlet.config._CONFIG_DIR", config_dir), \
             patch("gauntlet.config._CONFIG_FILE", config_file):
            _write_toml({"openai_key": "sk-abc", "anthropic_key": "sk-ant-xyz"})

            content = config_file.read_text()
            parsed = _parse_toml(content)
            assert parsed["openai_key"] == "sk-abc"
            assert parsed["anthropic_key"] == "sk-ant-xyz"

    def test_includes_header_comments(self, tmp_path: Path) -> None:
        """Written file should include header comments."""
        config_file = tmp_path / "config.toml"
        config_dir = tmp_path

        with patch("gauntlet.config._CONFIG_DIR", config_dir), \
             patch("gauntlet.config._CONFIG_FILE", config_file):
            _write_toml({"openai_key": "sk-test"})

            content = config_file.read_text()
            assert "# Gauntlet configuration" in content
