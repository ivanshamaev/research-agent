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

# ── Argument name aliases ─────────────────────────────────────────────────────
# Open-source LLMs often use different argument names than the schema specifies.
# Map known aliases → canonical names per tool.

_ARG_ALIASES: dict[str, dict[str, str]] = {
    "fetch_pages": {
        "url_list": "urls",
        "url":      "urls",
        "page_urls": "urls",
        "pages":    "urls",
        "links":    "urls",
        "page_list": "urls",
    },
    "search_web": {
        "search_query": "query",
        "search_term":  "query",
        "q":            "query",
        "search":       "query",
        "keywords":     "query",
        "num_results":  "max_results",
        "n_results":    "max_results",
        "count":        "max_results",
        "n":            "max_results",
        "limit":        "max_results",
        "k":            "max_results",
    },
    "summarize_page": {
        "text":         "content",
        "page_content": "content",
        "body":         "content",
        "topic":        "focus",
        "query":        "focus",
    },
    "write_report": {
        "body":           "content",
        "text":           "content",
        "report_content": "content",
        "report_title":   "title",
        "source_list":    "sources",
        "references":     "sources",
        "citations":      "sources",
    },
}


def _normalize_arg_names(tool_name: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Rename any aliased argument keys to their canonical names."""
    aliases = _ARG_ALIASES.get(tool_name, {})
    if not aliases:
        return kwargs
    return {aliases.get(k, k): v for k, v in kwargs.items()}


def _coerce_args(
    kwargs: dict[str, Any],
    input_schema: dict[str, Any],
) -> dict[str, Any]:
    """Coerce argument types to match the JSON Schema declaration.

    Open-source LLMs often produce string values for integer/array fields,
    or wrap arrays in JSON strings. This normalises them before dispatch.
    """
    import json as _json  # noqa: PLC0415

    properties: dict[str, Any] = input_schema.get("properties", {})
    result = dict(kwargs)

    for key, value in list(result.items()):
        prop_type = properties.get(key, {}).get("type")
        if prop_type == "integer" and not isinstance(value, int):
            try:
                result[key] = int(value)
            except (ValueError, TypeError):
                pass
        elif prop_type == "number" and not isinstance(value, (int, float)):
            try:
                result[key] = float(value)
            except (ValueError, TypeError):
                pass
        elif prop_type == "boolean" and not isinstance(value, bool):
            result[key] = str(value).lower() in ("true", "1", "yes")
        elif prop_type == "array":
            if isinstance(value, str):
                # LLM serialised array as JSON string: "[\"a\",\"b\"]"
                try:
                    parsed = _json.loads(value)
                    if isinstance(parsed, list):
                        result[key] = parsed
                except _json.JSONDecodeError:
                    # Treat bare string as single-element list
                    result[key] = [value]
            elif not isinstance(value, list):
                result[key] = [value]

    return result


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

    async def dispatch(self, tool_name: str, **kwargs: Any) -> Any:
        """Dispatch a tool call by name.

        Raises ToolError if tool_name is not registered.
        Propagates ToolError from tool implementations.
        Wraps unexpected exceptions in ToolError.
        """
        if tool_name not in self._dispatch:
            raise ToolError(f"Unknown tool: {tool_name}", tool_name=tool_name)

        # 1. Rename aliased argument names (e.g. url_list → urls)
        kwargs = _normalize_arg_names(tool_name, kwargs)
        # 2. Coerce types (e.g. "10" → 10 for integers, "[...]" → list)
        schema = self._schemas.get(tool_name, {})
        kwargs = _coerce_args(kwargs, schema.get("input_schema", {}))

        try:
            return await self._dispatch[tool_name](**kwargs)
        except ToolError:
            raise
        except Exception as e:
            raise ToolError(str(e), tool_name=tool_name) from e


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
