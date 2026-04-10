"""summarize_page — LLM-based text compression.

Compresses long page content into key points relevant to the research query.
Called when page content is too long to pass directly to the main LLM context.
"""

from __future__ import annotations

import structlog

from config.settings import settings
from tools.registry import ToolError

log = structlog.get_logger(__name__)

SUMMARIZE_PROMPT = """\
Summarize the following content, focusing on: {focus}

Extract the most important facts, statistics, and insights.
Be concise — aim for 200-400 words.

Content:
{content}
"""


async def summarize_page(
    content: str,
    focus: str = "key findings and insights",
) -> str:
    """Summarize content using LLM.

    Args:
        content: Full text content to summarize.
        focus: What aspect to focus the summary on.

    Returns:
        Concise summary string (200-400 words).

    Raises:
        ToolError: On LLM API failure.
    """
    try:
        import anthropic  # noqa: PLC0415

        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        prompt = SUMMARIZE_PROMPT.format(focus=focus, content=content[:12_000])

        message = await client.messages.create(
            model=settings.DEFAULT_MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )

        summary: str = message.content[0].text  # type: ignore[union-attr]
        log.info("summarize_done", chars_in=len(content), chars_out=len(summary))
        return summary

    except ToolError:
        raise
    except Exception as e:
        raise ToolError(str(e), tool_name="summarize_page") from e
