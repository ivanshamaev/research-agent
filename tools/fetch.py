"""fetch_pages — async concurrent HTTP fetch + HTML content extraction.

Fetches multiple URLs in parallel using asyncio.gather().
Parses HTML with BeautifulSoup, extracting readable text content.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from config.settings import settings
from tools.registry import ToolError

log = structlog.get_logger(__name__)

# Maximum content length per page (chars) to avoid filling context window
MAX_CONTENT_CHARS = 8_000


async def fetch_pages(
    urls: list[str],
) -> list[dict[str, str]]:
    """Fetch and extract text from multiple URLs concurrently.

    Args:
        urls: List of URLs to fetch. All fetched in parallel.

    Returns:
        List of dicts with keys: url, title, content, error (if failed).

    Raises:
        ToolError: Only if ALL urls fail. Individual failures are included
                   as entries with {"error": "..."} in the result list.

    Example return:
        [
            {"url": "https://...", "title": "Page Title", "content": "...text..."},
            {"url": "https://bad.url", "error": "Connection timeout"},
        ]
    """
    # TODO: implement
    # async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
    #     results = await asyncio.gather(
    #         *[_fetch_one(client, url) for url in urls],
    #         return_exceptions=True,
    #     )
    # return [r if not isinstance(r, Exception) else {"url": url, "error": str(r)} ...]
    raise NotImplementedError


async def _fetch_one(client: Any, url: str) -> dict[str, str]:
    """Fetch a single URL and extract text content.

    TODO: implement with BeautifulSoup
    - GET request with timeout
    - Parse HTML, extract <title> and main text
    - Strip scripts, styles, navigation
    - Truncate to MAX_CONTENT_CHARS
    """
    raise NotImplementedError
