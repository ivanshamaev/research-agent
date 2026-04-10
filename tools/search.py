"""search_web — web search via Tavily API.

Returns a list of search results with URLs, titles, and snippets.
The LLM uses these to decide which pages to fetch next.
"""

from __future__ import annotations

from typing import Any

import structlog

from config.settings import settings
from tools.registry import ToolError

log = structlog.get_logger(__name__)


async def search_web(
    query: str,
    max_results: int = 5,
) -> list[dict[str, str]]:
    """Search the web using Tavily API.

    Args:
        query: Search query string.
        max_results: Number of results to return (1-10).

    Returns:
        List of dicts with keys: url, title, snippet, score.

    Raises:
        ToolError: On API failure or missing API key.

    Example return:
        [
            {"url": "https://...", "title": "...", "snippet": "...", "score": "0.95"},
            ...
        ]
    """
    # TODO: implement using tavily-python SDK
    # from tavily import AsyncTavilyClient
    # client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)
    # response = await client.search(query, max_results=max_results)
    # return [{"url": r["url"], "title": r["title"], "snippet": r.get("content", "")} ...]
    raise NotImplementedError
