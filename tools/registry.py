"""ToolRegistry — central registry for all agent tools.

Responsibilities:
- Store tool schemas (JSON Schema format for Anthropic API)
- Dispatch tool calls by name to the correct async function
- Validate tool names before dispatch

All new tools MUST be registered here (schema + dispatch).
The orchestrator never calls tools directly — always through the registry.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

import structlog

log = structlog.get_logger(__name__)


# ── Exceptions ────────────────────────────────────────────────────────────────

class ToolError(Exception):
    """Raised by tools on recoverable failures.

    The orchestrator catches this and appends it as a tool result,
    allowing the LLM to reason about the failure and try alternatives.
    """
    def __init__(self, message: str, tool_name: str = "") -> None:
        super().__init__(message)
        self.tool_name = tool_name


# ── Tool schemas (JSON Schema for Anthropic API) ──────────────────────────────

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "search_web",
        "description": (
            "Search the internet for information on a topic. "
            "Returns a list of relevant URLs with titles and snippets. "
            "Use this first to discover sources."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query string. Be specific and include key terms.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (1-10). Default: 5.",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_pages",
        "description": (
            "Fetch and extract text content from one or more URLs in parallel. "
            "Returns cleaned text content for each page. "
            "Use after search_web to get full page content."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of URLs to fetch. Will be fetched concurrently.",
                },
            },
            "required": ["urls"],
        },
    },
    {
        "name": "summarize_page",
        "description": (
            "Summarize a long text into key points relevant to the research query. "
            "Use this when page content is too long to include directly."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The full text content to summarize.",
                },
                "focus": {
                    "type": "string",
                    "description": "What aspect to focus on when summarizing.",
                },
            },
            "required": ["content"],
        },
    },
    {
        "name": "write_report",
        "description": (
            "Synthesize all research findings into a final structured Markdown report. "
            "CALL THIS when you have gathered enough information. "
            "This terminates the research session."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Report title.",
                },
                "content": {
                    "type": "string",
                    "description": (
                        "Full Markdown report with sections, findings, and citations. "
                        "Include numbered references at the end."
                    ),
                },
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string"},
                            "title": {"type": "string"},
                        },
                        "required": ["url", "title"],
                    },
                    "description": "List of sources cited in the report.",
                },
            },
            "required": ["title", "content"],
        },
    },
]

# ── Tool dispatch table ───────────────────────────────────────────────────────

ToolFn = Callable[..., Awaitable[Any]]

# Populated at the bottom of this file after importing tool modules.
TOOL_DISPATCH: dict[str, ToolFn] = {}


# ── ToolRegistry ──────────────────────────────────────────────────────────────

class ToolRegistry:
    """Central registry: schema lookup + async dispatch.

    Usage:
        registry = ToolRegistry()
        schemas = registry.get_schemas()        # pass to LLM
        result = await registry.dispatch("search_web", query="RAG 2024")
    """

    def __init__(self) -> None:
        self._schemas: dict[str, dict[str, Any]] = {
            s["name"]: s for s in TOOL_SCHEMAS
        }
        self._dispatch = TOOL_DISPATCH

    def get_schemas(self) -> list[dict[str, Any]]:
        """Return all tool schemas in Anthropic API format."""
        return list(self._schemas.values())

    def list_tools(self) -> list[str]:
        """Return registered tool names."""
        return list(self._dispatch.keys())

    # TODO: implement
    async def dispatch(self, tool_name: str, **kwargs: Any) -> Any:
        """Dispatch a tool call by name.

        Raises ToolError if tool_name is not registered.
        Propagates ToolError from tool implementations.
        Wraps unexpected exceptions in ToolError.
        """
        raise NotImplementedError


# ── Register tools ────────────────────────────────────────────────────────────
# Import here (bottom) to avoid circular imports.
# Add new tool functions to TOOL_DISPATCH after implementing them.

def _register_tools() -> None:
    """Populate TOOL_DISPATCH with all tool functions."""
    try:
        from tools.search import search_web      # noqa: PLC0415
        from tools.fetch import fetch_pages      # noqa: PLC0415
        from tools.summarize import summarize_page  # noqa: PLC0415
        from tools.report import write_report    # noqa: PLC0415

        TOOL_DISPATCH.update({
            "search_web": search_web,
            "fetch_pages": fetch_pages,
            "summarize_page": summarize_page,
            "write_report": write_report,
        })
    except ImportError as e:
        log.warning("tool_import_failed", error=str(e))


_register_tools()
