# Урок 0.2. Архитектура проекта

## Карта компонентов

```mermaid
graph TD
    subgraph entry["Точка входа"]
        CLI["🖥️ main.py\nargparse · asyncio.run"]
    end

    subgraph core["Ядро агента  agent/"]
        Orch["⚙️ orchestrator.py\nReAct-цикл\nлимит шагов · инварианты"]
        State["💾 state.py\nAgentState\nсообщения · источники · отчёт"]
        LLM["🤖 llm_client.py\nAnthropicClient\nOpenAICompatibleClient"]
    end

    subgraph tools["Инструменты  tools/"]
        Registry["📋 registry.py\nTOOL_SCHEMAS\nTOOL_DISPATCH\nнормализация аргументов"]
        Search["🔍 search.py\nasyncio.to_thread\nDDGS"]
        Fetch["📥 fetch.py\nhttpx async\nBeautifulSoup"]
        Summ["📝 summarize.py\nAnthropic direct call"]
        Report["📄 report.py\nMarkdown formatter\nReportResult"]
    end

    subgraph infra["Инфраструктура"]
        Config["⚙️ config/settings.py\nPydantic Settings\n.env loader"]
        UI["🎨 ui/display.py\nRich console\nMarkdown render"]
    end

    CLI --> Orch
    Orch <--> State
    Orch --> LLM
    Orch --> Registry
    Registry --> Search
    Registry --> Fetch
    Registry --> Summ
    Registry --> Report
    Config -.->|настройки| LLM
    Config -.->|MAX_STEPS| Orch
    Orch --> UI

```

Каждый компонент отвечает за одну вещь — это принцип единственной
ответственности (Single Responsibility). Благодаря этому каждый модуль
можно тестировать и менять независимо.

---

## Поток данных: что происходит при одном запросе

```mermaid
sequenceDiagram
    actor U as 👤 Пользователь
    participant CLI as main.py
    participant Orch as Orchestrator
    participant State as AgentState
    participant LLM as LLMClient
    participant Reg as ToolRegistry
    participant Tool as Tool

    U->>CLI: python main.py "RAG best practices"
    CLI->>Orch: orchestrator.run("RAG best practices")
    Orch->>State: AgentState(query=...)
    Orch->>State: append_message(user: "Research topic...")

    loop ReAct-цикл (до MAX_STEPS или write_report)
        Orch->>LLM: complete(messages, tools, system)
        LLM-->>Orch: {stop_reason: "tool_use", tool: "search_web"}
        Orch->>State: append_message(assistant: tool_use)
        Orch->>Reg: dispatch("search_web", query=...)
        Reg->>Tool: search_web(query="RAG best practices")
        Tool-->>Reg: [{url, title, snippet}, ...]
        Reg-->>Orch: результаты
        Orch->>State: add_source(url, title)
        Orch->>State: append_message(user: tool_result)
    end

    Orch->>LLM: complete(messages, tools, system)
    LLM-->>Orch: {stop_reason: "tool_use", tool: "write_report"}
    Orch->>Reg: dispatch("write_report", title, content, sources)
    Reg->>Tool: write_report(...)
    Tool-->>Reg: ReportResult
    Reg-->>Orch: ReportResult
    Orch->>State: state.report = content

    Orch-->>CLI: AgentState
    CLI->>U: 📄 Отчёт в терминале
```

Разберём по шагам, что происходит когда вы запускаете:

```bash
python main.py "RAG best practices"
```

### Шаг 1 — CLI разбирает аргументы

`main.py` получает запрос, создаёт LLM-клиент и Orchestrator, запускает
`orchestrator.run("RAG best practices")`.

### Шаг 2 — Orchestrator инициализирует состояние

```python
state = AgentState(query="RAG best practices")
state.append_message(Message(role="user", content="Research topic: RAG best practices"))
```

`AgentState` — это «память» сессии. В ней хранится вся история переписки,
найденные источники и итоговый отчёт.

### Шаг 3 — Первый вызов LLM

Orchestrator отправляет историю сообщений и список доступных инструментов в LLM:

```python
response = await llm.complete(
    messages=state.to_api_messages(),
    tools=registry.get_schemas(),
    system=SYSTEM_PROMPT,
)
```

LLM видит инструменты (как функции с описанием) и решает, что нужно вызвать
`search_web`.

### Шаг 4 — Dispatch инструмента

LLM возвращает блок `tool_use`:

```json
{
  "type": "tool_use",
  "name": "search_web",
  "input": {"query": "RAG best practices 2024", "max_results": 5}
}
```

Orchestrator передаёт это в `ToolRegistry.dispatch()`, который находит
нужную функцию и вызывает её.

### Шаг 5 — Результат возвращается в контекст

Результат `search_web` добавляется в историю как сообщение от `user`:

```json
{
  "role": "user",
  "content": [{"type": "tool_result", "tool_use_id": "...", "content": "[...]"}]
}
```

Это стандарт Anthropic API — результаты инструментов передаются как
пользовательские сообщения, чтобы LLM видела их при следующем вызове.

### Шаг 6 — Цикл продолжается

Orchestrator снова вызывает LLM с обновлённой историей. LLM видит результаты
поиска и решает загрузить несколько страниц (`fetch_pages`). После загрузки —
снова вызов LLM. И так до тех пор, пока LLM не вызывает `write_report`.

### Шаг 7 — Завершение

Когда LLM вызывает `write_report`, Orchestrator:
1. Вызывает функцию `write_report` с переданным контентом
2. Сохраняет отчёт в `state.report`
3. **Немедленно** выходит из цикла

После этого `main.py` получает `state` и передаёт его в `ui/display.py`
для красивого вывода в терминал.

---

## Почему именно такая структура

### Почему AgentState отдельно от Orchestrator

Состояние (данные) и логика (что делать с данными) должны быть разделены.
Это упрощает тестирование: можно проверить `AgentState` без запуска цикла,
и проверить цикл с фиктивным состоянием.

### Почему ToolRegistry отдельно от инструментов

Оркестратор не знает о конкретных инструментах напрямую — он знает только
`ToolRegistry`. Это значит:
- Можно добавить новый инструмент, не трогая Orchestrator
- Можно тестировать диспетчер отдельно

### Почему LLMClient отдельно

LLM-клиент — это единственное место, где происходит общение с API.
Если завтра появится новый провайдер — меняем только клиент,
оркестратор не знает разницы.

---

## Структура файлов

```
research-agent/
├── main.py                    # Точка входа, CLI
│
├── agent/
│   ├── orchestrator.py        # ReAct-цикл
│   ├── state.py               # Память сессии
│   └── llm_client.py          # Работа с LLM API
│
├── tools/
│   ├── registry.py            # Каталог инструментов
│   ├── search.py              # Поиск в DuckDuckGo
│   ├── fetch.py               # Загрузка страниц
│   ├── summarize.py           # Суммаризация текста
│   └── report.py              # Финальный отчёт
│
├── config/
│   └── settings.py            # Настройки через .env
│
├── ui/
│   └── display.py             # Вывод в терминал (Rich)
│
└── tests/
    ├── conftest.py            # Общие фикстуры
    ├── test_tools.py          # Юнит-тесты инструментов
    └── test_agent.py          # Интеграционные тесты цикла
```

---

## Что дальше

Прежде чем смотреть на код — настроим окружение:
[03-setup.md](03-setup.md)
