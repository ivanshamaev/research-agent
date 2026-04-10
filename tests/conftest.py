"""conftest.py — shared fixtures for all tests.

Provides:
- MockLLMClient: scripted tool_use sequences for integration tests
- env_override: temporary environment variable injection
- sample_html: realistic HTML page for fetch tests
"""

from __future__ import annotations

import os
from typing import Any, AsyncIterator
from unittest.mock import AsyncMock

import pytest


# ── MockLLMClient ─────────────────────────────────────────────────────────────

class MockLLMClient:
    """LLM client that returns pre-scripted responses.

    Configure `responses` as a list of dicts in Anthropic response format.
    Each call to `complete()` pops the next response from the list.

    Usage:
        client = MockLLMClient([
            _tool_use("search_web", {"query": "test"}, "tu_001"),
            _tool_use("write_report", {"title": "T", "content": "C"}, "tu_002"),
        ])
        orchestrator = Orchestrator(llm=client)
        state = await orchestrator.run("test")
        assert state.report is not None
    """

    def __init__(self, responses: list[dict[str, Any]] | None = None) -> None:
        self._responses = list(responses or [])
        self._call_count = 0

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[Any],
        system: str = "",
    ) -> dict[str, Any]:
        self._call_count += 1
        if not self._responses:
            # Default: return write_report to terminate loop
            return _tool_use_response("write_report", {
                "title": "Test Report",
                "content": "# Test\n\nDefault mock report.",
                "sources": [],
            }, f"tu_default_{self._call_count}")
        return self._responses.pop(0)

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[Any],
        system: str = "",
    ) -> AsyncIterator[str]:
        yield "Mock streaming response"


def _tool_use_response(
    tool_name: str,
    tool_input: dict[str, Any],
    tool_use_id: str = "tu_001",
) -> dict[str, Any]:
    """Build a mock Anthropic API response with a tool_use block."""
    return {
        "id": f"msg_{tool_use_id}",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "tool_use",
                "id": tool_use_id,
                "name": tool_name,
                "input": tool_input,
            }
        ],
        "model": "claude-sonnet-4-6",
        "stop_reason": "tool_use",
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_llm_client() -> MockLLMClient:
    """Default mock LLM: search → write_report."""
    return MockLLMClient([
        _tool_use_response("search_web", {"query": "test query"}, "tu_001"),
        _tool_use_response("write_report", {
            "title": "Test Report",
            "content": "# Test Report\n\nFindings here.\n",
            "sources": [{"url": "https://example.com", "title": "Example"}],
        }, "tu_002"),
    ])


@pytest.fixture
def sample_html() -> str:
    """Realistic HTML page for fetch_pages tests."""
    return """<!DOCTYPE html>
<html>
<head><title>Test Page — RAG Best Practices</title></head>
<body>
  <nav>Navigation should be stripped</nav>
  <main>
    <h1>RAG Best Practices 2024</h1>
    <p>Retrieval-Augmented Generation combines dense retrieval with generation.</p>
    <p>Key techniques: hybrid search, reranking, and chunk size optimization.</p>
  </main>
  <script>alert('should be stripped')</script>
  <style>.hidden { display: none; }</style>
</body>
</html>"""


@pytest.fixture(autouse=True)
def mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject dummy API keys so settings validation passes in tests."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")
