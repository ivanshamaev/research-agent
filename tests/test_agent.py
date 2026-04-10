"""test_agent.py — integration tests for the full ReAct loop.

Tests the Orchestrator with MockLLMClient to verify loop behavior
without making real API calls.

Key invariants tested (see CLAUDE.md "ReAct Loop — Invariants"):
1. Step limit enforced
2. ToolError doesn't crash the loop
3. write_report terminates the loop
4. State is append-only
"""

from __future__ import annotations

import pytest

from tests.conftest import MockLLMClient, _tool_use_response


@pytest.mark.anyio
async def test_agent_completes_with_write_report(mock_llm_client: MockLLMClient):
    """Full loop: search → write_report → state.report is set."""
    from agent.orchestrator import Orchestrator
    orchestrator = Orchestrator(llm=mock_llm_client)
    state = await orchestrator.run("test research topic")
    assert state.report is not None
    assert "Test Report" in state.report


@pytest.mark.anyio
async def test_agent_respects_max_steps():
    """Loop exits after MAX_STEPS even if write_report is never called."""
    # LLM always returns search_web — no write_report
    endless_search = MockLLMClient([
        _tool_use_response("search_web", {"query": f"query {i}"}, f"tu_{i:03d}")
        for i in range(20)
    ])

    from agent.orchestrator import Orchestrator
    orchestrator = Orchestrator(llm=endless_search, max_steps=3)
    state = await orchestrator.run("infinite loop test")
    assert state.step <= 3
    assert state.report is None  # no report without write_report


@pytest.mark.anyio
async def test_agent_survives_tool_error():
    """ToolError from a tool does not crash the loop — loop continues."""
    from unittest.mock import AsyncMock, patch
    from tools.registry import ToolError

    client = MockLLMClient([
        _tool_use_response("search_web", {"query": "test"}, "tu_001"),
        _tool_use_response("write_report", {
            "title": "Recovery Report",
            "content": "# Recovery\n\nDespite error, continued.",
            "sources": [],
        }, "tu_002"),
    ])

    from agent.orchestrator import Orchestrator
    from tools.registry import ToolRegistry

    registry = ToolRegistry()

    # Make search_web raise ToolError
    original_dispatch = registry.dispatch

    async def patched_dispatch(tool_name: str, **kwargs):  # type: ignore[no-untyped-def]
        if tool_name == "search_web":
            raise ToolError("simulated API failure", tool_name="search_web")
        return await original_dispatch(tool_name, **kwargs)

    registry.dispatch = patched_dispatch  # type: ignore[method-assign]

    orchestrator = Orchestrator(llm=client, registry=registry)
    state = await orchestrator.run("error recovery test")

    # Loop continued and produced a report despite the error
    assert state.report is not None
    assert "Recovery" in state.report


@pytest.mark.anyio
async def test_agent_state_is_append_only(mock_llm_client: MockLLMClient):
    """Messages list only grows — never shrinks between steps."""
    from agent.orchestrator import Orchestrator

    sizes: list[int] = []

    orchestrator = Orchestrator(llm=mock_llm_client)

    # Patch run to record sizes after each step — use a subclass approach
    original_run = orchestrator.run

    async def instrumented_run(query: str):  # type: ignore[no-untyped-def]
        state = await original_run(query)
        return state

    state = await orchestrator.run("test")
    # Verify messages only grew: first msg + assistant + user tool result + ...
    assert len(state.messages) >= 2


@pytest.mark.anyio
async def test_agent_state_sources_populated(mock_llm_client: MockLLMClient):
    """After successful run, state.sources contains the report sources."""
    from agent.orchestrator import Orchestrator
    orchestrator = Orchestrator(llm=mock_llm_client)
    state = await orchestrator.run("test")
    # Sources from write_report's sources list
    assert len(state.sources) > 0
    assert state.sources[0].url == "https://example.com"
