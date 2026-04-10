# Research Agent

Автономный CLI-агент для исследования тем: ищет информацию в интернете,
параллельно загружает и суммаризирует страницы, синтезирует структурированный
Markdown-отчёт с источниками.

Проект Модуля 02 курса [AI Agent Roadmap — DataTalks.ru](https://datatalks.ru/ai-agents).

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

**Требования:** Python 3.11+, ключ любого LLM-провайдера, ключ Tavily API для веб-поиска.

```bash
# 1. Клонировать и установить
git clone <repo-url>
cd research-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. Настроить переменные окружения
cp .env.example .env
# Открыть .env, выбрать LLM_PROVIDER и вписать нужный API-ключ + TAVILY_API_KEY

# 3. Запустить агента
python main.py "Лучшие практики построения RAG-систем в 2024"
# или через установленный скрипт:
research-agent "Лучшие практики построения RAG-систем в 2024"
```
Пример заполнения .env
```
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-29712b12d60d43929f4d........
DEFAULT_MODEL=deepseek-chat

TAVILY_API_KEY=

LOG_LEVEL=INFO
MAX_STEPS=10
REQUEST_TIMEOUT=30
REPORTS_DIR=research/
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

## Поддерживаемые LLM-провайдеры

Агент работает с любым из перечисленных провайдеров. Достаточно одного ключа.

| Провайдер | `LLM_PROVIDER` | Рекомендуемые модели | Регистрация |
|-----------|----------------|----------------------|-------------|
| **Anthropic** | `anthropic` | `claude-sonnet-4-6`, `claude-opus-4-6`, `claude-haiku-4-5` | [console.anthropic.com](https://console.anthropic.com/) |
| **OpenAI** | `openai` | `gpt-4o`, `gpt-4o-mini`, `o1`, `o3-mini` | [platform.openai.com](https://platform.openai.com/api-keys) |
| **OpenRouter** | `openrouter` | `meta-llama/llama-3.3-70b-instruct`, `mistral/mistral-small-3.1-24b`, `google/gemini-2.0-flash-001` | [openrouter.ai](https://openrouter.ai/keys) |
| **DeepSeek** | `deepseek` | `deepseek-chat`, `deepseek-reasoner` | [platform.deepseek.com](https://platform.deepseek.com/api_keys) |
| **Qwen (Alibaba)** | `qwen` | `qwen-plus`, `qwen-turbo`, `qwen-max`, `qwen-long` | [dashscope.aliyuncs.com](https://dashscope.aliyuncs.com/) |
| **MiniMax** | `minimax` | `MiniMax-Text-01` | [minimaxi.chat](https://www.minimaxi.chat/) |
| **Ollama** (локально) | `ollama` | `llama3.2`, `mistral`, `gemma3`, `phi4`, `qwen2.5` | [ollama.com](https://ollama.com/) — бесплатно |

> **Через OpenRouter** доступно 300+ моделей: Claude, GPT-4o, Llama, Mistral, Gemini, Gemma и другие — по одному ключу.

### Настройка провайдера

Выберите провайдер в `.env`:

```bash
# Вариант 1 — Anthropic (по умолчанию)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_MODEL=claude-sonnet-4-6

# Вариант 2 — DeepSeek (дёшево, сильная модель)
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-...
DEFAULT_MODEL=deepseek-chat

# Вариант 3 — Ollama (бесплатно, локально, без ключа)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_MODEL=llama3.2
# Установка: ollama pull llama3.2

# Вариант 4 — OpenRouter (300+ моделей по одному ключу)
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
DEFAULT_MODEL=meta-llama/llama-3.3-70b-instruct
```

---

## Опции командной строки

```bash
python main.py "тема"                                          # базовый запуск
python main.py "тема" --provider deepseek --model deepseek-chat
python main.py "тема" --provider ollama --model llama3.2
python main.py "тема" --provider openrouter --model meta-llama/llama-3.3-70b-instruct
python main.py "тема" --max-steps 15                           # больше шагов
python main.py "тема" --save                                   # сохранить отчёт в research/
python main.py "тема" --verbose                                # DEBUG-лог для отладки

# После pip install -e . доступен короткий алиас:
research-agent "тема" --provider deepseek --save
```

---

## Переменные окружения

Все настройки — в файле `.env` (скопировать из `.env.example`):

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `LLM_PROVIDER` | `anthropic` | Провайдер: `anthropic` / `openai` / `openrouter` / `deepseek` / `qwen` / `minimax` / `ollama` |
| `ANTHROPIC_API_KEY` | — | Ключ Anthropic (нужен при `LLM_PROVIDER=anthropic`) |
| `OPENAI_API_KEY` | — | Ключ OpenAI (нужен при `LLM_PROVIDER=openai`) |
| `OPENROUTER_API_KEY` | — | Ключ OpenRouter |
| `DEEPSEEK_API_KEY` | — | Ключ DeepSeek |
| `QWEN_API_KEY` | — | Ключ Alibaba DashScope |
| `MINIMAX_API_KEY` | — | Ключ MiniMax |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL сервера Ollama |
| `TAVILY_API_KEY` | — | Ключ Tavily для веб-поиска (обязателен) |
| `DEFAULT_MODEL` | `claude-sonnet-4-6` | ID модели для выбранного провайдера |
| `MAX_STEPS` | `10` | Максимум шагов ReAct-цикла |
| `REQUEST_TIMEOUT` | `30` | Таймаут HTTP-запросов (сек) |
| `REPORTS_DIR` | `research/` | Папка для сохранения отчётов |
| `LOG_LEVEL` | `INFO` | Уровень логирования |

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
LOG_LEVEL=DEBUG python main.py "тема" --max-steps 3
# или:
python main.py "тема" --max-steps 3 --verbose
```

---

## Статус реализации

| Компонент | Статус |
|-----------|--------|
| Скаффолд проекта, CLAUDE.md | ✅ готово |
| `AgentState` — история и источники | ✅ готово |
| `LLMClient` — Anthropic SDK + стриминг | ✅ готово |
| `ToolRegistry` — схемы, регистрация, dispatch | ✅ готово |
| `search_web` — Tavily API | ✅ готово |
| `fetch_pages` — async httpx + BS4 | ✅ готово |
| `summarize_page` — LLM-сжатие | ✅ готово |
| `write_report` — финальный отчёт | ✅ готово |
| `Orchestrator` — ReAct-цикл (5 инвариантов) | ✅ готово |
| `display.py` — Rich UI | ✅ готово |
| Юнит и интеграционные тесты (28/28) | ✅ готово |

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
