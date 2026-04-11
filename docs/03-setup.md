# Урок 0.3. Установка и настройка окружения

## Требования

- Python 3.11 или новее
- API-ключ хотя бы одного LLM-провайдера (или Ollama локально — бесплатно)
- Интернет (для поиска через DuckDuckGo)

Проверить версию Python:
```bash
python3 --version
# Python 3.11.x или 3.12.x
```

---

## Установка

### 1. Клонировать репозиторий

```bash
git clone <repo-url>
cd research-agent
```

### 2. Создать виртуальное окружение

Виртуальное окружение изолирует зависимости проекта от системного Python.
Это хорошая практика — каждый проект живёт в своём «пузыре».

```bash
python3 -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows
```

После активации в начале строки терминала появится `(.venv)`.

### 3. Установить зависимости

```bash
pip install -e ".[dev]"
```

Флаг `-e` означает «editable install» — пакет устанавливается в режиме
разработки: изменения в коде вступают в силу немедленно без переустановки.
`[dev]` добавляет инструменты для разработки: pytest, ruff, mypy.

---

## Настройка переменных окружения

### Что такое .env файл

Вместо того чтобы хранить секретные ключи прямо в коде (что опасно),
их принято хранить в специальном файле `.env` в корне проекта.
Этот файл не коммитится в git (он уже в `.gitignore`).

### Создать .env из шаблона

```bash
cp .env.example .env
```

Откройте `.env` в редакторе и заполните нужные значения.

---

## Выбор LLM-провайдера

В агенте есть поддержка 9 провайдеров. Нужен только один ключ.

### Вариант 1 — GateLLM (рекомендуется для старта)

GateLLM — российский OpenAI-совместимый шлюз с доступом к Qwen, Llama и другим
открытым моделям. Можно использовать тестовый ключ из примера.

```env
LLM_PROVIDER=gatellm
GATELLM_API_KEY=sk-37f6008381068c81f06a00ce4a8b19229c43f8ae55a25a57fbfee94f49e4671c
DEFAULT_MODEL=qwen/qwen-2.5-72b-instruct
```

Быстрый старт GateLLM:
1. Зарегистрируйтесь на [gatellm.ru](https://gatellm.ru/)
2. Создайте ключ в разделе «API ключи»
3. Эндпоинт: `https://gatellm.ru/v1/` (OpenAI-совместимый)

### Вариант 2 — Anthropic (Claude)

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_MODEL=claude-sonnet-4-6
```

Получить ключ: [console.anthropic.com](https://console.anthropic.com/)

### Вариант 3 — DeepSeek (дёшево, мощная модель)

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-...
DEFAULT_MODEL=deepseek-chat
```

Получить ключ: [platform.deepseek.com](https://platform.deepseek.com/)

### Вариант 4 — Ollama (бесплатно, работает локально)

Ollama запускает модели прямо на вашем компьютере. Никаких ключей не нужно.

```bash
# Установить Ollama
sudo snap install ollama        # Ubuntu
# или: https://ollama.com/download

# Скачать модель (один раз)
ollama pull llama3.2
```

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_MODEL=llama3.2
```

### Вариант 5 — OpenRouter (300+ моделей по одному ключу)

```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
DEFAULT_MODEL=meta-llama/llama-3.3-70b-instruct
```

---

## Полный список переменных .env

```env
# ── Провайдер ─────────────────────────────────────────────────
LLM_PROVIDER=gatellm          # anthropic | openai | openrouter |
                              # deepseek | qwen | minimax | ollama |
                              # gatellm | custom

# ── API-ключи (нужен только один) ────────────────────────────
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
OPENROUTER_API_KEY=
DEEPSEEK_API_KEY=
QWEN_API_KEY=
MINIMAX_API_KEY=
GATELLM_API_KEY=

# ── Специальные настройки провайдеров ────────────────────────
OLLAMA_BASE_URL=http://localhost:11434
CUSTOM_API_BASE_URL=          # для LLM_PROVIDER=custom
CUSTOM_API_KEY=

# ── Модель ───────────────────────────────────────────────────
DEFAULT_MODEL=qwen/qwen-2.5-72b-instruct

# ── Параметры агента ──────────────────────────────────────────
MAX_STEPS=10                  # максимум итераций ReAct-цикла
REQUEST_TIMEOUT=30            # таймаут HTTP-запросов (сек)
REPORTS_DIR=research/         # куда сохранять отчёты

# ── Логирование ───────────────────────────────────────────────
LOG_LEVEL=INFO                # DEBUG | INFO | WARNING | ERROR
```

---

## Проверка установки

```bash
# Запустить тесты — все должны пройти
pytest tests/ -x -q

# Проверить список инструментов
python3 -c "from tools.registry import ToolRegistry; print(ToolRegistry().list_tools())"
# ['search_web', 'fetch_pages', 'summarize_page', 'write_report']

# Первый запуск агента
python main.py "Что такое RAG?" --max-steps 5
```

---

## Опции командной строки

```bash
python main.py "тема"                           # базовый запуск
python main.py "тема" --provider deepseek       # выбор провайдера
python main.py "тема" --model deepseek-chat     # выбор модели
python main.py "тема" --max-steps 15            # больше шагов
python main.py "тема" --save                    # сохранить в research/
python main.py "тема" --verbose                 # DEBUG-логи
```

---

## Что дальше

Окружение готово. Начинаем разбирать код по компонентам:
[04-agent-state.md](04-agent-state.md)
