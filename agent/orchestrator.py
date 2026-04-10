"""Orchestrator — ReAct loop: Reason → Act → Observe → repeat.

Central component. All changes here must preserve the five loop invariants
documented in CLAUDE.md under "ReAct Loop — Invariants".
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from agent.llm_client import LLMClientProtocol, create_llm_client
from agent.state import AgentState, Message, Source
from config.settings import settings
from tools.registry import ToolError, ToolRegistry

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
        self.llm = llm or create_llm_client()
        self.registry = registry or ToolRegistry()
        self.max_steps = max_steps or settings.MAX_STEPS

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
        state = AgentState(query=query)
        state.append_message(self._build_initial_message(query))

        tools = self.registry.get_schemas()

        while state.step < self.max_steps:
            state.increment_step()
            log.info("react_step", step=state.step, max_steps=self.max_steps)

            response = await self.llm.complete(
                messages=state.to_api_messages(),
                tools=tools,
                system=SYSTEM_PROMPT,
            )

            # Append assistant turn to history (invariant 4: append-only)
            state.append_message(Message(role="assistant", content=response["content"]))

            stop_reason = response.get("stop_reason", "")

            # Pure text response — no tool calls
            if stop_reason == "end_turn":
                log.info("llm_end_turn", step=state.step)
                break

            if stop_reason != "tool_use":
                log.warning("unexpected_stop_reason", stop_reason=stop_reason, step=state.step)
                break

            # Process all tool_use blocks in this response
            tool_results: list[dict[str, Any]] = []
            done = False

            for block in response["content"]:
                if block.get("type") != "tool_use":
                    continue

                tool_name: str = block["name"]
                tool_input: dict[str, Any] = block["input"]
                tool_use_id: str = block["id"]

                result_str = await self._dispatch_tool(state, tool_name, tool_input, tool_use_id)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result_str,
                })

                # Invariant 5: write_report exits immediately
                if tool_name == "write_report":
                    done = True
                    break

            # Append all tool results as a single user message (Anthropic API requirement)
            if tool_results:
                state.append_message(Message(role="user", content=tool_results))

            if done:
                log.info("react_done", reason="write_report", step=state.step)
                break
        else:
            log.warning("react_max_steps_reached", step=state.step)

        return state

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
        # Invariant 2: every dispatch logged
        log.info(
            "tool_dispatched",
            tool=tool_name,
            step=state.step,
            input_preview=str(tool_input)[:120],
        )

        try:
            result = await self.registry.dispatch(tool_name, **tool_input)

            if tool_name == "write_report":
                # result is a ReportResult — extract content and sources
                state.report = result.content
                for src in result.sources:
                    state.add_source(Source(
                        url=src.get("url", ""),
                        title=src.get("title", ""),
                    ))
                return f"Report written: {result.title} ({result.word_count} words)"

            if tool_name == "search_web" and isinstance(result, list):
                for r in result:
                    if r.get("url"):
                        state.add_source(Source(
                            url=r["url"],
                            title=r.get("title", ""),
                            snippet=r.get("snippet", ""),
                        ))

            # Convert result to a readable string for the LLM
            if isinstance(result, str):
                return result
            return json.dumps(result, ensure_ascii=False, default=str)

        except ToolError as e:
            # Invariant 3: ToolError never crashes loop
            log.warning("tool_error", tool=tool_name, error=str(e), step=state.step)
            return f"Error executing {tool_name}: {e}"

    def _build_initial_message(self, query: str) -> Message:
        return Message(role="user", content=f"Research topic: {query}")
