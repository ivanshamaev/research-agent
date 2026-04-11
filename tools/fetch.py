"""fetch_pages — async concurrent HTTP fetch + HTML content extraction.

Fetches multiple URLs in parallel using asyncio.gather().
Parses HTML with BeautifulSoup, extracting readable text content.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup

from config.settings import settings
from tools.registry import ToolError

log = structlog.get_logger(__name__)

# Maximum content length per page (chars) to avoid filling context window.
# 5 pages × 3000 chars = ~15k chars ≈ 4k tokens — safe for most providers.
MAX_CONTENT_CHARS = 3_000


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
    async with httpx.AsyncClient(
        timeout=settings.REQUEST_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "ResearchAgent/0.1 (educational bot)"},
    ) as client:
        raw_results = await asyncio.gather(
            *[_fetch_one(client, url) for url in urls],
            return_exceptions=True,
        )

    output: list[dict[str, str]] = []
    for url, result in zip(urls, raw_results):
        if isinstance(result, Exception):
            log.warning("fetch_failed", url=url, error=str(result))
            output.append({"url": url, "error": str(result)})
        else:
            output.append(result)  # type: ignore[arg-type]

    success_count = sum(1 for r in output if "error" not in r)
    log.info("fetch_pages_done", total=len(urls), success=success_count)

    return output


async def _fetch_one(client: httpx.AsyncClient, url: str) -> dict[str, str]:
    """Fetch a single URL and extract text content using BeautifulSoup."""
    response = await client.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else url

    # Remove noise elements
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
        tag.decompose()

    # Extract main text
    text = soup.get_text(separator="\n", strip=True)

    # Collapse excessive blank lines
    lines = [line for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)

    if len(text) > MAX_CONTENT_CHARS:
        text = text[:MAX_CONTENT_CHARS] + "\n... [truncated]"

    return {"url": url, "title": title, "content": text}
