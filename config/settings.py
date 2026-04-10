"""Settings — Pydantic Settings with .env loading.

Validates all required environment variables on startup.
Import `settings` from this module — do not instantiate Settings directly.

Usage:
    from config.settings import settings
    print(settings.DEFAULT_MODEL)
    print(settings.MAX_STEPS)
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration for the Research Agent.

    Values are loaded from environment variables and .env file.
    Required fields raise ValidationError on startup if missing.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── API keys ───────────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = Field(
        default="",
        description="Anthropic Claude API key. Required for production.",
    )
    TAVILY_API_KEY: str = Field(
        default="",
        description="Tavily web search API key. Required for production.",
    )

    # ── LLM ───────────────────────────────────────────────────────────────────
    DEFAULT_MODEL: str = Field(
        default="claude-sonnet-4-6",
        description="Anthropic model ID to use for the agent.",
    )

    # ── Agent loop ────────────────────────────────────────────────────────────
    MAX_STEPS: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Hard limit on ReAct loop iterations.",
    )

    # ── HTTP ──────────────────────────────────────────────────────────────────
    REQUEST_TIMEOUT: int = Field(
        default=30,
        ge=5,
        le=120,
        description="HTTP request timeout in seconds.",
    )

    # ── Output ────────────────────────────────────────────────────────────────
    REPORTS_DIR: str = Field(
        default="research/",
        description="Directory where finished reports are saved.",
    )

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Log level: DEBUG, INFO, WARNING, ERROR.",
    )


# Singleton instance — import this everywhere
settings = Settings()
