from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All app configuration lives here. Values come from environment variables or a .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "OpsPilot"
    environment: str = "local"   # local | staging | production
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Create Settings once, then reuse it everywhere."""
    return Settings()