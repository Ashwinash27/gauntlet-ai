"""Configuration management for Gauntlet.

Manages ~/.gauntlet/config.toml for storing API keys and settings.
Falls back to environment variables.
"""

import os
from pathlib import Path

from gauntlet.exceptions import ConfigError

_CONFIG_DIR = Path.home() / ".gauntlet"
_CONFIG_FILE = _CONFIG_DIR / "config.toml"

# Valid config keys and their env var equivalents
_KEY_MAP = {
    "openai_key": "OPENAI_API_KEY",
    "anthropic_key": "ANTHROPIC_API_KEY",
    "embedding_model": "GAUNTLET_EMBEDDING_MODEL",
    "embedding_threshold": "GAUNTLET_EMBEDDING_THRESHOLD",
    "llm_model": "GAUNTLET_LLM_MODEL",
    "llm_timeout": "GAUNTLET_LLM_TIMEOUT",
}


def _ensure_config_dir() -> None:
    """Create config directory if it doesn't exist."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _parse_toml(text: str) -> dict[str, str]:
    """Minimal TOML parser for flat key-value pairs.

    Only supports `key = "value"` format - sufficient for our config.
    """
    result: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("["):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip quotes
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        result[key] = value
    return result


def _write_toml(data: dict[str, str]) -> None:
    """Write config data as TOML."""
    _ensure_config_dir()
    lines = ["# Gauntlet configuration", "# https://github.com/your-org/gauntlet", ""]
    for key, value in sorted(data.items()):
        lines.append(f'{key} = "{value}"')
    lines.append("")
    _CONFIG_FILE.write_text("\n".join(lines))
    # Set restrictive permissions (owner read/write only)
    try:
        _CONFIG_FILE.chmod(0o600)
    except OSError:
        pass  # Windows doesn't support Unix permissions


def load_config() -> dict[str, str]:
    """Load configuration from file.

    Returns:
        Dictionary of config key-value pairs.
    """
    if not _CONFIG_FILE.exists():
        return {}
    try:
        return _parse_toml(_CONFIG_FILE.read_text())
    except Exception as e:
        raise ConfigError(f"Failed to read config: {e}")


def get_config_value(key: str) -> str | None:
    """Get a config value with fallback chain.

    Resolution order:
    1. Config file (~/.gauntlet/config.toml)
    2. Environment variables

    Args:
        key: The config key to look up.

    Returns:
        The config value, or None if not found.
    """
    # 1. Config file
    config = load_config()
    if key in config:
        return config[key]

    # 2. Environment variable
    env_var = _KEY_MAP.get(key)
    if env_var:
        value = os.environ.get(env_var)
        if value:
            return value

    return None


def set_config_value(key: str, value: str) -> None:
    """Set a config value in the config file.

    Args:
        key: The config key.
        value: The config value.
    """
    if key not in _KEY_MAP:
        raise ConfigError(f"Unknown config key: {key}. Valid keys: {', '.join(_KEY_MAP)}")

    config = load_config()
    config[key] = value
    _write_toml(config)


def list_config() -> dict[str, str | None]:
    """List all config values with their sources.

    Returns:
        Dictionary of key -> value (with source indicator).
    """
    result: dict[str, str | None] = {}
    config = load_config()

    for key, env_var in _KEY_MAP.items():
        if key in config:
            value = config[key]
            # Mask sensitive values
            if "key" in key.lower() and value:
                masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                result[key] = f"{masked} (config file)"
            else:
                result[key] = f"{value} (config file)"
        elif os.environ.get(env_var):
            value = os.environ[env_var]
            if "key" in key.lower() and value:
                masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                result[key] = f"{masked} (env: {env_var})"
            else:
                result[key] = f"{value} (env: {env_var})"
        else:
            result[key] = None

    return result


def get_openai_key() -> str | None:
    """Get OpenAI API key from config or env."""
    return get_config_value("openai_key")


def get_anthropic_key() -> str | None:
    """Get Anthropic API key from config or env."""
    return get_config_value("anthropic_key")


__all__ = [
    "load_config",
    "get_config_value",
    "set_config_value",
    "list_config",
    "get_openai_key",
    "get_anthropic_key",
]
