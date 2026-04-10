# Research Agent — CLAUDE.md

> Instructions for Claude Code. Read this file before making any changes.
> This file describes the architecture, conventions, and rules for iterative development.

---

## Project Overview

Research Agent is a CLI tool that autonomously researches any topic:
searches the web, fetches and summarizes pages concurrently, and synthesizes
a structured Markdown report with citations.

**Pattern:** ReAct loop — LLM decides which tools to call; the orchestrator
executes them and feeds results back until `write_report` is invoked.

**Stack:** Python 3.11+, httpx (async), Anthropic SDK, Pydantic v2, Rich, structlog.

**Status:** Scaffolded — stubs in place, core logic not yet implemented.
Implement iteratively: `AgentState` → `LLMClient` → `ToolRegistry` → tools → `Orchestrator`.

---

## Architecture

```
CLI (main.py)
  └─► Orchestrator (agent/orchestrator.py)    ← ReAct loop, step counter, stop condition
        ├─► AgentState (agent/state.py)        ← message history, scratchpad, sources
        ├─► LLMClient (agent/llm_client.py)    ← Anthropic SDK, streaming, retry
        └─► ToolRegistry (tools/registry.py)   ← registration, JSON Schema, dispatch
              ├─► search_web    (tools/search.py)     → Tavily API
              ├─► fetch_pages   (tools/fetch.py)      → httpx + BeautifulSoup
              ├─► summarize_page (tools/summarize.py) → LLM compression
              └─► write_report  (tools/report.py)     → LLM + Markdown
```

**Data flow:**
1. `main.py` parses CLI args → calls `Orchestrator.run(query)`
2. Orchestrator sends messages + tool schemas to LLM
3. LLM returns `tool_use` block → Orchestrator dispatches via `ToolRegistry`
4. Tool result appended to `AgentState` → next LLM call
5. LLM calls `write_report` → loop exits → report printed via `ui/display.py`

---

## Key Files

| File | Role | Edit notes |
|------|------|-----------|
| `agent/orchestrator.py` | ReAct loop | Central file — changes affect all tool execution |
| `agent/state.py` | `AgentState` dataclass | Message history + scratchpad + sources |
| `agent/llm_client.py` | LLM abstraction | Anthropic SDK; streaming + retry |
| `tools/registry.py` | Tool registration + dispatch | **All new tools must be registered here** |
| `tools/search.py` | `search_web` tool | Tavily REST API |
| `tools/fetch.py` | `fetch_pages` tool | Concurrent async HTTP + HTML parsing |
| `tools/summarize.py` | `summarize_page` tool | LLM-based compression |
| `tools/report.py` | `write_report` tool | Terminal condition — produces final report |
| `config/settings.py` | Pydantic Settings | Loads `.env`, validates keys on startup |
| `ui/display.py` | Rich output | Progress, spinners, Markdown render |

---

## Setup & Commands

```bash
# Install (from project root)
pip install -e ".[dev]"

# Copy env template and fill in keys
cp .env.example .env

# Run the agent
python -m research_agent "Best practices for building RAG systems"

# Run with options
python -m research_agent "topic" --model claude-sonnet-4-6 --max-steps 15 --save

# Run tests
pytest tests/ -x -v

# Linting + types
ruff check . && mypy agent/ tools/ config/
```

---

## Code Conventions

### Async everywhere
All I/O (HTTP, LLM calls) **must use async/await**.
`fetch_pages` uses `asyncio.gather()` — do not convert to sync.

### Adding a new tool — required steps
1. Create `tools/your_tool.py` with `async def your_tool(...) -> ToolResult`
2. Define input schema as a `TypedDict` or Pydantic model in the same file
3. Add full JSON Schema to `TOOL_SCHEMAS` in `tools/registry.py`
   - Every property needs a `description` field
   - List all required fields explicitly
4. Register in `TOOL_DISPATCH` dict in `tools/registry.py`
5. Write unit test in `tests/test_tools.py` with mocked HTTP/LLM
6. Verify: `python -c "from tools.registry import ToolRegistry; r = ToolRegistry(); print(r.list_tools())"`

### Logging
Use `structlog` only — **never `print()` in agent or tool code**.
Exception: `ui/display.py` uses Rich console directly.

```python
import structlog
log = structlog.get_logger(__name__)
log.info("tool_dispatched", tool_name="search_web", step=step, query=query)
```

### Error handling
Tools raise `ToolError(message, tool_name)` on recoverable failures.
Orchestrator catches `ToolError`, appends it as tool result, continues loop.
**Do not raise bare `Exception` from tool code.**

### Type hints
All public functions and methods require type hints.
Private helpers (`_prefixed`) are optional.

### Imports
Group imports: stdlib → third-party → local. Use absolute imports within the package.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | — | Claude API key |
| `TAVILY_API_KEY` | Yes | — | Web search API key |
| `DEFAULT_MODEL` | No | `claude-sonnet-4-6` | LLM model ID |
| `MAX_STEPS` | No | `10` | Hard stop for ReAct loop |
| `REQUEST_TIMEOUT` | No | `30` | HTTP timeout in seconds |
| `LOG_LEVEL` | No | `INFO` | `DEBUG` for full tool traces |
| `REPORTS_DIR` | No | `research/` | Where to save reports |

**Security:** Never commit `.env`. The `.gitignore` already excludes it — do not remove that rule.

---

## Testing

### Run
```bash
pytest tests/ -x -v          # stop on first failure, verbose
pytest tests/test_tools.py   # tools only
pytest tests/test_agent.py   # integration loop
```

### Unit tests (`tests/test_tools.py`)
Test each tool in isolation. Mock HTTP with `respx`:
```python
import respx, httpx, pytest

@pytest.mark.anyio
@respx.mock
async def test_fetch_pages_parses_html():
    respx.get("https://example.com").mock(
        return_value=httpx.Response(200, text="<h1>Hello World</h1>")
    )
    from tools.fetch import fetch_pages
    results = await fetch_pages(["https://example.com"])
    assert "Hello World" in results[0]["content"]
```

### Integration tests (`tests/test_agent.py`)
Use `MockLLMClient` from `tests/conftest.py` which returns scripted `tool_use` sequences.

### What NOT to mock
- **Never mock `ToolRegistry`** — test real dispatch to catch JSON Schema mismatches
- **Never mock `AgentState`** — it's a plain dataclass, instantiate directly
- **Do mock** Tavily API, Anthropic API, all external HTTP

---

## ReAct Loop — Invariants

These must hold after any change to `orchestrator.py`:

1. **Step limit enforced** — loop exits after `MAX_STEPS` even without `write_report`
2. **Every tool dispatch logged** — `log.info("tool_dispatched", tool=name, step=step)`
3. **ToolError never crashes loop** — caught, appended as tool result, loop continues
4. **State is append-only** — never delete or mutate existing messages in `AgentState.messages`
5. **write_report always terminates** — receiving `write_report` in `tool_use` exits the loop immediately

---

## Anti-Patterns

### 1. Sync HTTP in async tools
```python
# WRONG
result = requests.get(url).text

# CORRECT
async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
    response = await client.get(url)
```

### 2. Tool without JSON Schema
Every tool dispatched by LLM needs a complete schema in `TOOL_SCHEMAS`.
Missing or wrong schema → LLM hallucinates arguments.

### 3. Mutable default in AgentState
```python
# WRONG — shared mutable state across instances
messages: list = []

# CORRECT
messages: list = field(default_factory=list)
```

### 4. Hardcoded model names
Never write `"claude-sonnet-4-6"` in tool/orchestrator code.
Always use `settings.DEFAULT_MODEL`.

### 5. print() in agent loop
Use `structlog`. Unexpected `print()` corrupts Rich's live display.

### 6. Skipping token budget trim
`llm_client.py` enforces a token budget via `_trim_history()`.
Do not remove or bypass it — it prevents silent truncation API errors.

---

## Common Workflows

### Implementing a stub
Each stub has a `raise NotImplementedError` or `TODO` comment.
Implement in dependency order: `state.py` → `llm_client.py` → `registry.py` → tools → `orchestrator.py`.

### Debugging a stuck ReAct loop
```bash
LOG_LEVEL=DEBUG python -m research_agent "test topic" --max-steps 3
```
Check structlog output for `tool_dispatched` events.
Missing events = LLM not calling tools → inspect system prompt in `orchestrator.py`.

### Changing LLM provider
Swap `agent/llm_client.py`. The `LLMClientProtocol` defines the interface:
```python
class LLMClientProtocol(Protocol):
    async def complete(
        self, messages: list[Message], tools: list[ToolSchema]
    ) -> LLMResponse: ...
```

---

## Project Roadmap

- [x] Project scaffold and stubs
- [x] CLAUDE.md and AGENTS.md
- [ ] `AgentState` — implement append_message, to_api_messages
- [ ] `LLMClient` — Anthropic SDK integration with streaming
- [ ] `ToolRegistry` — registration, schema validation, dispatch
- [ ] `search_web` — Tavily API integration
- [ ] `fetch_pages` — async concurrent httpx + BeautifulSoup
- [ ] `summarize_page` — LLM page compression
- [ ] `write_report` — final Markdown synthesis
- [ ] `Orchestrator` — full ReAct loop with all invariants
- [ ] `display.py` — Rich UI (progress, Markdown render)
- [ ] Integration tests passing end-to-end
- [ ] CLI polish (`--save`, `--model`, `--verbose`)
