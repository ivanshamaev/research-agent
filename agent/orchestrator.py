"""Orchestrator — ReAct loop: Reason → Act → Observe → repeat.

Central component. All changes here must preserve the five loop invariants
documented in CLAUDE.md under "ReAct Loop — Invariants".
"""

from __future__ import annotations

from typing import Any

import structlog

from agent.llm_client import AnthropicClient, LLMClientProtocol
from agent.state import AgentState, Message, Source
from config.settings import settings
from tools.registry import ToolRegistry

log = structlog.get_logger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a research assistant that autonomously investigates topics.

You have access to these tools:
- search_web: search the internet for information
- fetch_pages: download and extract content from URLs
- summarize_page: compress long page content into key points
- write_report: synthesize findings into a final Markdown report (call this when done)

Research process:
1. Start with broad searches to find relevant sources
2. Fetch the most promising pages
3. Summarize content to extract key information
4. Do additional searches if needed to fill gaps
5. Call write_report when you have enough information

Be thorough but efficient. Prefer parallel tool calls when possible.
Always include source URLs in your final report.
"""


# ── Orchestrator ──────────────────────────────────────────────────────────────

class Orchestrator:
    """Runs the ReAct loop for a research query.

    Invariants (must hold after any change):
    1. Step limit enforced — exits after max_steps even without write_report
    2. Every tool dispatch logged at INFO level
    3. ToolError never crashes the loop — appended as tool result
    4. State is append-only — messages are never deleted
    5. write_report always terminates — exits loop immediately
    """

    def __init__(
        self,
        llm: LLMClientProtocol | None = None,
        registry: ToolRegistry | None = None,
        max_steps: int | None = None,
    ) -> None:
        self.llm = llm or AnthropicClient()
        self.registry = registry or ToolRegistry()
        self.max_steps = max_steps or settings.MAX_STEPS

    # TODO: implement
    async def run(self, query: str) -> AgentState:
        """Execute the full ReAct loop for a research query.

        Returns the final AgentState with report and sources populated.

        Steps:
        1. Init AgentState with the user query as first message
        2. Loop until write_report is called or max_steps reached:
           a. Call LLM with current messages + tool schemas
           b. If text response → append to state, continue
           c. If tool_use → dispatch via registry, append result, log
           d. If write_report in tool_use → set state.report, break
        3. Return state
        """
        raise NotImplementedError

    # TODO: implement
    async def _dispatch_tool(
        self,
        state: AgentState,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_use_id: str,
    ) -> str:
        """Dispatch a single tool call and return the result as a string.

        Catches ToolError and returns it as an error string (never raises).
        Logs every dispatch at INFO level.
        Updates state.sources if the tool returns source data.
        """
        raise NotImplementedError

    def _build_initial_message(self, query: str) -> Message:
        return Message(role="user", content=f"Research topic: {query}")
