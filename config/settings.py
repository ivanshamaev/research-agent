"""Settings — Pydantic Settings with .env loading.

Validates all required environment variables on startup.
Import `settings` from this module — do not instantiate Settings directly.

Usage:
    from config.settings import settings
    print(settings.DEFAULT_MODEL)
    print(settings.LLM_PROVIDER)
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# All supported LLM providers
LLMProvider = Literal[
    "anthropic",
    "openai",
    "openrouter",
    "deepseek",
    "qwen",
    "minimax",
    "ollama",
]


class Settings(BaseSettings):
    """All configuration for the Research Agent.

    Values are loaded from environment variables and .env file.
    Set LLM_PROVIDER to choose which LLM backend to use.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Provider selector ─────────────────────────────────────────────────────
    LLM_PROVIDER: LLMProvider = Field(
        default="anthropic",
        description=(
            "Which LLM provider to use. "
            "Options: anthropic, openai, openrouter, deepseek, qwen, minimax, ollama"
        ),
    )

    # ── API keys (set only the ones you need) ────────────────────────────────
    ANTHROPIC_API_KEY: str = Field(
        default="",
        description="Anthropic Claude API key. Required when LLM_PROVIDER=anthropic.",
    )
    OPENAI_API_KEY: str = Field(
        default="",
        description="OpenAI API key. Required when LLM_PROVIDER=openai.",
    )
    OPENROUTER_API_KEY: str = Field(
        default="",
        description="OpenRouter API key. Required when LLM_PROVIDER=openrouter.",
    )
    DEEPSEEK_API_KEY: str = Field(
        default="",
        description="DeepSeek API key. Required when LLM_PROVIDER=deepseek.",
    )
    QWEN_API_KEY: str = Field(
        default="",
        description="Alibaba DashScope API key. Required when LLM_PROVIDER=qwen.",
    )
    MINIMAX_API_KEY: str = Field(
        default="",
        description="MiniMax API key. Required when LLM_PROVIDER=minimax.",
    )

    # ── Local / Ollama ────────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL. Used when LLM_PROVIDER=ollama.",
    )

    # ── Search ────────────────────────────────────────────────────────────────
    TAVILY_API_KEY: str = Field(
        default="",
        description="Tavily web search API key. Required for search_web tool.",
    )

    # ── LLM ───────────────────────────────────────────────────────────────────
    DEFAULT_MODEL: str = Field(
        default="claude-sonnet-4-6",
        description=(
            "Model ID to use. Must match the chosen provider. "
            "Examples: claude-sonnet-4-6, gpt-4o, deepseek-chat, qwen-plus, "
            "mistral/mistral-small-3.1-24b (OpenRouter), llama3.2 (Ollama)."
        ),
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
