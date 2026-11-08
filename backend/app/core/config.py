"""Centralized application configuration and environment settings.

Provides strongly typed configuration management via Pydantic Settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings schema with environment variable overrides."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: str = "development"
    DATABASE_URL: str | None = None
    SYNC_DATABASE_URL: str | None = None
    OPENROUTER_API_KEY: str | None = None
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8001,"
        "http://127.0.0.1:8001,http://localhost:8000,http://127.0.0.1:8000"
    )

    DEFAULT_BASELINE_MODELS: list[str] = [
        "mock-frontier-v1",
        "mock-compact-v1",
        "mock-heuristic-v1",
    ]
    AVAILABLE_LIVE_MODELS: list[str] = [
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.2-11b-vision-instruct:free",
        "openai/gpt-4o-mini",
    ]

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS_ORIGINS into list of trimmed strings."""
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()
DEFAULT_BASELINE_MODELS = settings.DEFAULT_BASELINE_MODELS
AVAILABLE_LIVE_MODELS = settings.AVAILABLE_LIVE_MODELS
