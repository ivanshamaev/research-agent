# Research Agent

Автономный CLI-агент для исследования тем: ищет информацию в интернете,
параллельно загружает и суммаризирует страницы, синтезирует структурированный
Markdown-отчёт с источниками.

Проект Модуля 02 курса [AI Agent Roadmap — DataTalks.ru](https://datatalk.ru).

---

## Как это работает

Агент реализует паттерн **ReAct (Reason + Act)**:

```
Запрос пользователя
      ↓
  Orchestrator  ←──────────────────────────────────────────────────────┐
      ↓                                                                  │
   LLM думает: нужен инструмент?                                        │
      ├── search_web("RAG best practices 2024")                         │
      │       ↓ 8 результатов                                           │
      ├── fetch_pages(["url1", "url2"])  ← параллельно                  │
      │       ↓ содержимое страниц                                      │
      ├── summarize_page(content)                                        │
      │       ↓ сжатые тезисы                              ещё цикл? ──┘
      └── write_report(title, content, sources)
              ↓
         Готовый отчёт в Markdown
```

LLM сам решает, сколько шагов нужно. Цикл завершается, когда она вызывает
`write_report`, или принудительно после `MAX_STEPS` итераций.

---

## Быстрый старт

**Требования:** Python 3.11+, ключи Anthropic API и Tavily API.

```bash
# 1. Клонировать и установить
git clone <repo-url>
cd research-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. Настроить переменные окружения
cp .env.example .env
# Открыть .env и вписать ANTHROPIC_API_KEY и TAVILY_API_KEY

# 3. Запустить агента
python -m research_agent "Лучшие практики построения RAG-систем в 2024"
```

Пример вывода:

```
╔═══════════════════════════════════════════╗
║  Research Agent  ·  v0.1  ·  DataTalks.ru ║
╚═══════════════════════════════════════════╝

Шаг 1  search_web("RAG best practices 2024")
   → 8 результатов · 0.4 сек

Шаг 2  fetch_pages(["arxiv.org/...", "lilianweng.github.io/..."])
   → 2 страницы параллельно · 1.2 сек

Шаг 3  write_report()
   → Синтезирую отчёт...

# Лучшие практики RAG-систем (2024)
...
```

---

## Опции командной строки

```bash
python -m research_agent "тема"                      # базовый запуск
python -m research_agent "тема" --max-steps 15       # больше шагов для глубокого исследования
python -m research_agent "тема" --model claude-opus-4-6  # другая модель
python -m research_agent "тема" --save               # сохранить отчёт в research/
python -m research_agent "тема" --verbose            # DEBUG-лог для отладки
```

---

## Переменные окружения

Все настройки — в файле `.env` (скопировать из `.env.example`):

| Переменная | Обязательна | По умолчанию | Описание |
|------------|-------------|--------------|----------|
| `ANTHROPIC_API_KEY` | да | — | Ключ Claude API |
| `TAVILY_API_KEY` | да | — | Ключ Tavily для веб-поиска |
| `DEFAULT_MODEL` | нет | `claude-sonnet-4-6` | ID модели Anthropic |
| `MAX_STEPS` | нет | `10` | Максимум шагов ReAct-цикла |
| `REQUEST_TIMEOUT` | нет | `30` | Таймаут HTTP-запросов (сек) |
| `REPORTS_DIR` | нет | `research/` | Папка для сохранения отчётов |
| `LOG_LEVEL` | нет | `INFO` | Уровень логирования |

---

## Структура проекта

```
research-agent/
├── main.py                    # CLI: argparse, точка входа
│
├── agent/
│   ├── orchestrator.py        # ReAct-цикл, счётчик шагов, условие остановки
│   ├── state.py               # AgentState: история сообщений, скрэтчпад, источники
│   └── llm_client.py          # Anthropic SDK: стриминг, retry, бюджет токенов
│
├── tools/
│   ├── registry.py            # Реестр инструментов: JSON Schema + диспетчер
│   ├── search.py              # search_web  → Tavily API
│   ├── fetch.py               # fetch_pages → httpx async + BeautifulSoup
│   ├── summarize.py           # summarize_page → LLM-сжатие
│   └── report.py              # write_report → терминальный инструмент
│
├── config/
│   └── settings.py            # Pydantic Settings, загрузка .env
│
├── ui/
│   └── display.py             # Rich: прогресс, спиннер, Markdown-рендер
│
├── tests/
│   ├── conftest.py            # MockLLMClient, фикстуры
│   ├── test_tools.py          # Юнит-тесты инструментов (mocked HTTP)
│   └── test_agent.py          # Интеграционные тесты цикла (mock LLM)
│
├── research/                  # Сохранённые отчёты (gitignored)
├── CLAUDE.md                  # Инструкции для Claude Code
├── pyproject.toml
└── .env.example
```

---

## Разработка

### Запуск тестов

```bash
pytest tests/ -x -v            # остановиться на первой ошибке
pytest tests/test_tools.py     # только тесты инструментов
pytest tests/test_agent.py     # только интеграционные тесты
```

### Линтер и проверка типов

```bash
ruff check .
mypy agent/ tools/ config/
```

### Добавить новый инструмент

1. Создать `tools/your_tool.py` с `async def your_tool(...) -> ...`
2. Добавить JSON Schema в `TOOL_SCHEMAS` в `tools/registry.py`
3. Зарегистрировать функцию в `TOOL_DISPATCH` в `tools/registry.py`
4. Написать юнит-тест в `tests/test_tools.py` с mocked HTTP

### Отладка зависшего цикла

```bash
LOG_LEVEL=DEBUG python -m research_agent "тема" --max-steps 3
```

---

## Статус реализации

| Компонент | Статус |
|-----------|--------|
| Скаффолд проекта, CLAUDE.md | ✅ готово |
| `ToolRegistry` — схемы и регистрация | ✅ готово |
| `AgentState` — история и источники | ⬜ стаб |
| `LLMClient` — Anthropic SDK + стриминг | ⬜ стаб |
| `search_web` — Tavily API | ⬜ стаб |
| `fetch_pages` — async httpx + BS4 | ⬜ стаб |
| `summarize_page` — LLM-сжатие | ⬜ стаб |
| `write_report` — финальный отчёт | ⬜ стаб |
| `Orchestrator` — ReAct-цикл | ⬜ стаб |
| `display.py` — Rich UI | ⬜ стаб |
| Интеграционные тесты | ⬜ разблокируются по мере реализации |

Порядок реализации: `AgentState` → `LLMClient` → `ToolRegistry.dispatch` → инструменты → `Orchestrator`

---

## Технологии

- **[Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python)** — Claude API, tool calling, стриминг
- **[httpx](https://www.python-httpx.org/)** — async HTTP-клиент для параллельных запросов
- **[BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)** — парсинг HTML
- **[Pydantic v2](https://docs.pydantic.dev/)** — валидация настроек и данных
- **[Rich](https://rich.readthedocs.io/)** — красивый терминальный UI
- **[structlog](https://www.structlog.org/)** — структурированное логирование
- **[Tavily](https://tavily.com/)** — API веб-поиска, оптимизированный для LLM
- **[pytest](https://pytest.org/) + [respx](https://lundberg.github.io/respx/)** — тесты с mocked HTTP
