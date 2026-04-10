"""main.py — CLI entry point for the Research Agent.

Usage:
    python -m research_agent "Your research topic here"
    python -m research_agent "topic" --model claude-sonnet-4-6 --max-steps 15 --save
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger(__name__)


def _configure_logging(level: str) -> None:
    """Set up structlog with console renderer."""
    import logging  # noqa: PLC0415
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="research-agent",
        description="Autonomous research agent using ReAct loop",
    )
    parser.add_argument("query", help="Research topic or question")
    parser.add_argument(
        "--model",
        default=None,
        help="Override default LLM model (e.g. claude-sonnet-4-6)",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Override MAX_STEPS from settings",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save report to REPORTS_DIR after completion",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging",
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    """Main async entry point. Returns exit code."""
    from config.settings import settings  # noqa: PLC0415
    from agent.orchestrator import Orchestrator  # noqa: PLC0415
    from ui.display import print_banner, print_report, print_summary  # noqa: PLC0415

    # Apply CLI overrides
    if args.model:
        settings.DEFAULT_MODEL = args.model
    if args.max_steps:
        settings.MAX_STEPS = args.max_steps

    print_banner()

    orchestrator = Orchestrator()

    try:
        state = await orchestrator.run(args.query)
    except KeyboardInterrupt:
        log.info("interrupted_by_user")
        return 130

    print_report(state)
    print_summary(state)

    if args.save and state.report:
        _save_report(state, settings.REPORTS_DIR)

    return 0


def _save_report(state: Any, reports_dir: str) -> None:
    """Save the report to a Markdown file in REPORTS_DIR."""
    from ui.display import console  # noqa: PLC0415

    dir_path = Path(reports_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r"[^\w\s-]", "", state.query).strip()
    safe_name = re.sub(r"\s+", "_", safe_name)[:60] or "report"
    file_path = dir_path / f"{safe_name}.md"

    file_path.write_text(state.report, encoding="utf-8")
    log.info("report_saved", path=str(file_path))
    console.print(f"\n[green]Report saved →[/green] {file_path}")


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    _configure_logging("DEBUG" if args.verbose else "INFO")

    exit_code = asyncio.run(_run(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
