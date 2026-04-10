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
    # Show up to 2 key args, truncated for readability
    preview_items = list(tool_input.items())[:2]
    args_str = ", ".join(f"{k}={str(v)[:50]!r}" for k, v in preview_items)
    console.print(f"\n[bold cyan]Step {step}[/bold cyan] → [yellow]{tool_name}[/yellow]({args_str})")


@contextmanager
def thinking_spinner(message: str = "Thinking...") -> Generator[None, None, None]:
    """Context manager that shows a spinner while the LLM is thinking."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task(message, total=None)
        yield


def print_report(state: AgentState) -> None:
    """Render the final report as Markdown to the terminal."""
    if not state.report:
        console.print("[red]No report generated.[/red]")
        return

    console.print("\n")
    console.rule("[bold blue]Research Report[/bold blue]")
    console.print(Markdown(state.report))
    print_sources(state)


def print_sources(state: AgentState) -> None:
    """Print a formatted table of all sources found during research."""
    if not state.sources:
        return

    table = Table(
        title="Sources",
        show_header=True,
        header_style="bold blue",
        show_lines=False,
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="green", no_wrap=False)
    table.add_column("URL", style="cyan", no_wrap=False)

    for i, source in enumerate(state.sources, 1):
        table.add_row(str(i), source.title or "—", source.url)

    console.print("\n")
    console.print(table)


def print_summary(state: AgentState) -> None:
    """Print session summary: steps used, tool calls, sources found."""
    console.print(
        f"\n[dim]Steps: {state.step}  ·  "
        f"Sources: {len(state.sources)}  ·  "
        f"Messages: {len(state.messages)}[/dim]"
    )
