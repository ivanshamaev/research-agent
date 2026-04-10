"""write_report — terminal tool that synthesizes the final research report.

This tool is the stop condition for the ReAct loop.
When the orchestrator sees write_report in a tool_use block, it must:
1. Call this function to format the report
2. Set state.report to the result
3. Exit the loop immediately

Do NOT call this tool multiple times in one session.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

log = structlog.get_logger(__name__)


@dataclass
class ReportResult:
    """Structured result from write_report."""
    title: str
    content: str
    sources: list[dict[str, str]]
    word_count: int


async def write_report(
    title: str,
    content: str,
    sources: list[dict[str, str]] | None = None,
) -> ReportResult:
    """Format and return the final research report.

    Args:
        title: Report title.
        content: Full Markdown content with sections and inline citations.
        sources: List of {"url": ..., "title": ...} dicts for the reference section.

    Returns:
        ReportResult with formatted Markdown content.

    Note:
        This function formats the report — it does NOT call the LLM.
        The LLM already wrote the content in the tool_use call.
        We just assemble the final document structure here.
    """
    sources = sources or []

    full_content = content

    if sources:
        refs = "\n\n## References\n\n"
        for i, src in enumerate(sources, 1):
            src_title = src.get("title") or src.get("url", "")
            src_url = src.get("url", "")
            refs += f"{i}. [{src_title}]({src_url})\n"
        full_content = content.rstrip() + refs

    word_count = len(full_content.split())

    log.info("report_written", title=title, word_count=word_count, sources=len(sources))

    return ReportResult(
        title=title,
        content=full_content,
        sources=sources,
        word_count=word_count,
    )
