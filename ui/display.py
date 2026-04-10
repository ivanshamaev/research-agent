"""display.py — Rich terminal UI for the Research Agent.

Handles all terminal output:
- Animated spinner during LLM thinking
- Step progress display with tool name + args
- Final report rendered as Markdown
- Source list formatting

This is the only module allowed to use Rich console directly (not structlog).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from agent.state import AgentState

console = Console()


def print_banner() -> None:
    """Print the Research Agent startup banner."""
    console.print(Panel(
        "[bold blue]Research Agent[/bold blue]  ·  v0.1  ·  DataTalks.ru",
        border_style="dim blue",
    ))


def print_step(step: int, tool_name: str, tool_input: dict[str, Any]) -> None:
    """Print a step header when a tool is being called."""
    # TODO: implement — show step number, tool name, key input args
    raise NotImplementedError


@contextmanager
def thinking_spinner(message: str = "Thinking...") -> Generator[None, None, None]:
    """Context manager that shows a spinner while the LLM is thinking."""
    # TODO: implement using Rich Progress with SpinnerColumn
    raise NotImplementedError
    yield


def print_report(state: AgentState) -> None:
    """Render the final report as Markdown to the terminal."""
    if not state.report:
        console.print("[red]No report generated.[/red]")
        return
    # TODO: implement — render state.report as Markdown, then print sources table
    raise NotImplementedError


def print_sources(state: AgentState) -> None:
    """Print a formatted table of all sources found during research."""
    if not state.sources:
        return
    # TODO: implement — Rich Table with URL, title columns
    raise NotImplementedError


def print_summary(state: AgentState) -> None:
    """Print session summary: steps used, tool calls, sources found."""
    console.print(
        f"\n[dim]Steps: {state.step}  ·  "
        f"Sources: {len(state.sources)}  ·  "
        f"Messages: {len(state.messages)}[/dim]"
    )
