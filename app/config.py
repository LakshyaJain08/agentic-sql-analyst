import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_ENV: str = "development"
    API_PORT: int = 8000
    STREAMLIT_PORT: int = 8501

    # LLM Settings
    LLM_PROVIDER: str = "gemini"  # gemini, openai, anthropic, or mock
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gemini-1.5-flash"
    LLM_TEMPERATURE: float = 0.0

    # Database Settings
    DATABASE_URL: str = "sqlite:///./ecommerce.db"
    
    # Query Safety Limits
    QUERY_TIMEOUT_SECONDS: int = 10
    MAX_RESULT_ROWS: int = 500
    MAX_SQL_RETRIES: int = 2


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton instance of application settings."""
    return Settings()
