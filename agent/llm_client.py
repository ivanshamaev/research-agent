"""LLMClient — Anthropic SDK wrapper with streaming, retry, and token budget.

Implements LLMClientProtocol so the orchestrator is decoupled from the provider.
Use AnthropicClient for production; MockLLMClient in tests (see tests/conftest.py).
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Protocol, runtime_checkable

import structlog

from config.settings import settings

log = structlog.get_logger(__name__)

# ── Type aliases ──────────────────────────────────────────────────────────────

ToolSchema = dict[str, Any]
LLMResponse = dict[str, Any]  # raw Anthropic response object


# ── Protocol ──────────────────────────────────────────────────────────────────

@runtime_checkable
class LLMClientProtocol(Protocol):
    """Interface that all LLM client implementations must satisfy."""

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolSchema],
        system: str = "",
    ) -> LLMResponse:
        """Send messages and return the full response (no streaming)."""
        ...

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolSchema],
        system: str = "",
    ) -> AsyncIterator[str]:
        """Send messages and yield text deltas as they arrive."""
        ...


# ── Token budget ──────────────────────────────────────────────────────────────

def _estimate_tokens(messages: list[dict[str, Any]]) -> int:
    """Rough token estimate: ~4 chars per token."""
    text = str(messages)
    return len(text) // 4


def _trim_history(
    messages: list[dict[str, Any]],
    max_tokens: int = 80_000,
) -> list[dict[str, Any]]:
    """Remove oldest messages to stay within token budget.

    Always keeps the first user message (the original query) and
    all messages from the last N turns.
    Do not remove or bypass — prevents silent truncation API errors.
    """
    if _estimate_tokens(messages) <= max_tokens:
        return messages

    # Keep first message + trim from index 1
    trimmed = [messages[0]] + messages[1:]
    while len(trimmed) > 2 and _estimate_tokens(trimmed) > max_tokens:
        trimmed.pop(1)

    log.warning("history_trimmed", kept=len(trimmed), original=len(messages))
    return trimmed


# ── Anthropic client ──────────────────────────────────────────────────────────

class AnthropicClient:
    """Production LLM client using the Anthropic SDK.

    Handles:
    - Non-streaming completion with tool schemas
    - Streaming text output
    - Exponential backoff retry on rate limits
    - Token budget enforcement via _trim_history()
    """

    def __init__(
        self,
        model: str | None = None,
        max_retries: int = 3,
        max_tokens: int = 4096,
    ) -> None:
        self.model = model or settings.DEFAULT_MODEL
        self.max_retries = max_retries
        self.max_tokens = max_tokens
        self._client: Any = None  # lazy init to avoid import errors in tests

    def _get_client(self) -> Any:
        """Lazy import so tests can run without the SDK installed."""
        if self._client is None:
            import anthropic  # noqa: PLC0415
            self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._client

    # TODO: implement
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolSchema],
        system: str = "",
    ) -> LLMResponse:
        """Call Anthropic messages API and return the full response.

        Applies token budget trimming and exponential backoff retry.
        On tool_use response, returns the raw message object for orchestrator parsing.
        """
        raise NotImplementedError

    # TODO: implement
    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolSchema],
        system: str = "",
    ) -> AsyncIterator[str]:
        """Stream text deltas from the Anthropic messages API."""
        raise NotImplementedError
        yield  # make this a generator function

    async def _with_retry(self, coro_fn: Any, *args: Any, **kwargs: Any) -> Any:
        """Retry coroutine with exponential backoff on rate limit errors."""
        for attempt in range(self.max_retries):
            try:
                return await coro_fn(*args, **kwargs)
            except Exception as e:
                if "rate_limit" in str(e).lower() and attempt < self.max_retries - 1:
                    wait = 2 ** attempt
                    log.warning("rate_limit_retry", attempt=attempt + 1, wait=wait)
                    await asyncio.sleep(wait)
                else:
                    raise
