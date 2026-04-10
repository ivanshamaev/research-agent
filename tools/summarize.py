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
    # TODO: implement
    # Use a direct Anthropic API call (not the orchestrator's LLM client)
    # to avoid polluting the main conversation history.
    # import anthropic
    # client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    # message = await client.messages.create(
    #     model=settings.DEFAULT_MODEL,
    #     max_tokens=600,
    #     messages=[{"role": "user", "content": SUMMARIZE_PROMPT.format(...)}]
    # )
    # return message.content[0].text
    raise NotImplementedError
