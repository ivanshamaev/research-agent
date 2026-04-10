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
    # TODO: uncomment when Orchestrator is implemented
    # from agent.orchestrator import Orchestrator
    # orchestrator = Orchestrator(llm=mock_llm_client)
    # state = await orchestrator.run("test research topic")
    # assert state.report is not None
    # assert "Test Report" in state.report
    pytest.skip("Orchestrator not implemented yet")


@pytest.mark.anyio
async def test_agent_respects_max_steps():
    """Loop exits after MAX_STEPS even if write_report is never called."""
    # LLM always returns search_web — no write_report
    endless_search = MockLLMClient([
        _tool_use_response("search_web", {"query": f"query {i}"}, f"tu_{i:03d}")
        for i in range(20)
    ])

    # TODO: uncomment when Orchestrator is implemented
    # from agent.orchestrator import Orchestrator
    # orchestrator = Orchestrator(llm=endless_search, max_steps=3)
    # state = await orchestrator.run("infinite loop test")
    # assert state.step <= 3
    # assert state.report is None  # no report without write_report
    pytest.skip("Orchestrator not implemented yet")


@pytest.mark.anyio
async def test_agent_survives_tool_error():
    """ToolError from a tool does not crash the loop — loop continues."""
    # TODO: implement when ToolError handling is in place
    pytest.skip("Orchestrator not implemented yet")


@pytest.mark.anyio
async def test_agent_state_is_append_only(mock_llm_client: MockLLMClient):
    """Messages list only grows — never shrinks between steps."""
    # TODO: uncomment when Orchestrator is implemented
    # from agent.orchestrator import Orchestrator
    # orchestrator = Orchestrator(llm=mock_llm_client)
    # sizes = []
    # # Patch to observe state at each step...
    # state = await orchestrator.run("test")
    # assert all(sizes[i] <= sizes[i+1] for i in range(len(sizes)-1))
    pytest.skip("Orchestrator not implemented yet")


@pytest.mark.anyio
async def test_agent_state_sources_populated(mock_llm_client: MockLLMClient):
    """After successful run, state.sources contains the report sources."""
    # TODO: uncomment when Orchestrator is implemented
    # from agent.orchestrator import Orchestrator
    # orchestrator = Orchestrator(llm=mock_llm_client)
    # state = await orchestrator.run("test")
    # assert len(state.sources) > 0
    # assert state.sources[0].url == "https://example.com"
    pytest.skip("Orchestrator not implemented yet")
