"""AgentState — message history, scratchpad, and source list for the ReAct loop.

This is the single source of truth for everything the agent knows during a session.
State is append-only: never delete or mutate existing messages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# ── Message types ─────────────────────────────────────────────────────────────

Role = Literal["user", "assistant"]


@dataclass
class ToolUse:
    """Represents a single tool call made by the LLM."""
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class ToolResult:
    """Result returned from a tool execution."""
    tool_use_id: str
    content: str
    is_error: bool = False


@dataclass
class Message:
    """A single message in the conversation history."""
    role: Role
    content: str | list[Any]  # str for text, list for tool_use/tool_result blocks


@dataclass
class Source:
    """A web source cited in the research."""
    url: str
    title: str
    snippet: str = ""


# ── AgentState ────────────────────────────────────────────────────────────────

@dataclass
class AgentState:
    """Full state of one research session.

    Holds the conversation history in Anthropic message format,
    a scratchpad for intermediate LLM reasoning traces,
    and a deduplicated list of sources found during research.
    """
    query: str
    messages: list[Message] = field(default_factory=list)
    scratchpad: list[str] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    step: int = 0
    report: str | None = None

    # TODO: implement
    def append_message(self, message: Message) -> None:
        """Append a message to the conversation history (append-only)."""
        raise NotImplementedError

    # TODO: implement
    def add_source(self, source: Source) -> None:
        """Add a source, deduplicating by URL."""
        raise NotImplementedError

    # TODO: implement
    def to_api_messages(self) -> list[dict[str, Any]]:
        """Convert messages to the format expected by the Anthropic API."""
        raise NotImplementedError

    def increment_step(self) -> None:
        self.step += 1

    def __repr__(self) -> str:
        return (
            f"AgentState(query={self.query!r}, "
            f"steps={self.step}, "
            f"messages={len(self.messages)}, "
            f"sources={len(self.sources)})"
        )
