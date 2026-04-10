"""test_tools.py — unit tests for individual tools.

Each tool is tested in isolation with mocked external dependencies.
Do NOT mock ToolRegistry — test real dispatch to catch schema mismatches.
"""

from __future__ import annotations

import pytest
import respx
import httpx

from tools.registry import ToolRegistry, ToolError


# ── search_web ────────────────────────────────────────────────────────────────

@pytest.mark.anyio
@respx.mock
async def test_search_web_returns_results():
    """search_web returns a list of results with url, title, snippet."""
    respx.post("https://api.tavily.com/search").mock(
        return_value=httpx.Response(200, json={
            "results": [
                {"url": "https://example.com", "title": "Example", "content": "snippet", "score": 0.9},
            ]
        })
    )
    from tools.search import search_web
    results = await search_web("test query", max_results=1)
    assert len(results) == 1
    assert results[0]["url"] == "https://example.com"
    assert results[0]["title"] == "Example"
    assert "snippet" in results[0]


@pytest.mark.anyio
@respx.mock
async def test_search_web_raises_tool_error_on_api_failure():
    """search_web raises ToolError (not raw exception) on API failure."""
    respx.post("https://api.tavily.com/search").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    from tools.search import search_web
    with pytest.raises(ToolError):
        await search_web("test query")


# ── fetch_pages ───────────────────────────────────────────────────────────────

@pytest.mark.anyio
@respx.mock
async def test_fetch_pages_extracts_text(sample_html: str):
    """fetch_pages returns extracted text, strips scripts and nav."""
    respx.get("https://example.com/").mock(
        return_value=httpx.Response(200, text=sample_html)
    )

    from tools.fetch import fetch_pages
    results = await fetch_pages(["https://example.com/"])
    assert len(results) == 1
    assert "RAG Best Practices" in results[0]["content"]
    assert "alert(" not in results[0]["content"]  # script stripped


@pytest.mark.anyio
@respx.mock
async def test_fetch_pages_handles_failed_url():
    """fetch_pages includes error entry for failed URLs, doesn't raise."""
    respx.get("https://bad-url.example/").mock(
        side_effect=httpx.ConnectError("connection refused")
    )

    from tools.fetch import fetch_pages
    results = await fetch_pages(["https://bad-url.example/"])
    assert results[0].get("error") is not None


@pytest.mark.anyio
@respx.mock
async def test_fetch_pages_concurrent(sample_html: str):
    """fetch_pages fetches multiple URLs concurrently."""
    for i in range(3):
        respx.get(f"https://example{i}.com/").mock(
            return_value=httpx.Response(200, text=sample_html)
        )

    from tools.fetch import fetch_pages
    results = await fetch_pages([f"https://example{i}.com/" for i in range(3)])
    assert len(results) == 3
    assert all("content" in r for r in results)



# ── write_report ──────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_write_report_returns_formatted_markdown():
    """write_report assembles content + sources into a ReportResult."""
    from tools.report import write_report

    result = await write_report(
        title="Test Report",
        content="# Test\n\nSome findings.",
        sources=[{"url": "https://example.com", "title": "Example"}],
    )

    assert result.title == "Test Report"
    assert "## References" in result.content
    assert "https://example.com" in result.content
    assert result.word_count > 0
    assert len(result.sources) == 1


@pytest.mark.anyio
async def test_write_report_no_sources():
    """write_report works when sources list is empty."""
    from tools.report import write_report

    result = await write_report(title="T", content="# T\n\nContent.", sources=[])
    assert "## References" not in result.content
    assert result.word_count > 0


# ── ToolRegistry dispatch ─────────────────────────────────────────────────────

def test_registry_lists_all_tools():
    """ToolRegistry lists all four expected tools."""
    registry = ToolRegistry()
    tools = registry.list_tools()
    assert "search_web" in tools
    assert "fetch_pages" in tools
    assert "summarize_page" in tools
    assert "write_report" in tools


def test_registry_schemas_have_descriptions():
    """Every tool schema has a description on all required properties."""
    registry = ToolRegistry()
    for schema in registry.get_schemas():
        assert "description" in schema, f"{schema['name']} missing top-level description"
        for prop_name, prop in schema["input_schema"]["properties"].items():
            assert "description" in prop, (
                f"{schema['name']}.{prop_name} missing property description"
            )


@pytest.mark.anyio
async def test_registry_raises_tool_error_on_unknown_tool():
    """Registry raises ToolError for unknown tool names."""
    registry = ToolRegistry()
    with pytest.raises(ToolError, match="Unknown tool"):
        await registry.dispatch("unknown_tool", query="test")
