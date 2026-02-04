"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars not in model
    )

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""

    # OpenAI (for embeddings)
    openai_api_key: str = ""

    # Anthropic (for LLM judge)
    anthropic_api_key: str = ""

    # Environment
    environment: str = "development"

    # Detection settings
    embedding_model: str = "text-embedding-3-small"
    embedding_threshold: float = 0.55
    layer3_timeout: float = 3.0
    max_input_length: int = 10000

    # Rate limiting
    default_rate_limit: int = 1000  # requests per day

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
