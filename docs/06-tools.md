# Урок 3. Инструменты агента — Tools

**Папка:** `tools/`

## Что такое инструмент агента

Инструмент — это обычная Python-функция, которую LLM может вызвать.
LLM не запускает код сама — она лишь возвращает в ответе структуру
«хочу вызвать функцию X с аргументами Y». Ваш код перехватывает это
и выполняет реальный вызов.

Каждый инструмент:
1. Принимает аргументы (LLM передаёт их по схеме)
2. Делает что-то полезное (HTTP-запрос, обработка текста)
3. Возвращает результат, который уходит обратно в контекст LLM

---

## Инструмент 1: search_web

**Файл:** `tools/search.py`

### Что делает

Ищет в DuckDuckGo и возвращает список URL с заголовками и сниппетами.
Это первый шаг в любом исследовании.

### Реализация

```python
async def search_web(query: str, max_results: int = 5) -> list[dict[str, str]]:
    results = await asyncio.to_thread(_ddg_search, query, max_results)
    return results
```

### Ключевое решение: asyncio.to_thread

Библиотека `ddgs` (DuckDuckGo) работает **синхронно** — она блокирует
поток исполнения пока ждёт ответа от сети.

Наш агент работает **асинхронно** (async/await). Если вызвать синхронную
функцию напрямую, она заблокирует весь event loop — другие задачи не смогут
выполняться.

Решение — `asyncio.to_thread()`: запускает синхронную функцию в отдельном
потоке, не блокируя event loop.

```python
# НЕПРАВИЛЬНО — блокирует event loop:
results = DDGS().text(query)

# ПРАВИЛЬНО — запускает в пуле потоков:
results = await asyncio.to_thread(DDGS().text, query)
```

### Обработка ошибок

```python
def _ddg_search(query, max_results):
    try:
        raw = DDGS().text(query, max_results=max_results) or []
    except (RatelimitException, TimeoutException, DDGSException) as e:
        raise ToolError(str(e), tool_name="search_web") from e  # ← управляемое исключение
```

`ToolError` — специальный класс исключений для инструментов.
Оркестратор перехватывает его и передаёт LLM как результат с ошибкой,
позволяя ей попробовать другой подход. Цикл не прерывается.

### Формат возврата

```python
[
    {"url": "https://arxiv.org/...", "title": "RAG Survey 2024", "snippet": "..."},
    {"url": "https://example.com/...", "title": "RAG Guide", "snippet": "..."},
]
```

---

## Инструмент 2: fetch_pages

**Файл:** `tools/fetch.py`

### Что делает

Загружает несколько страниц параллельно и извлекает из них читаемый текст
(без HTML-тегов, скриптов, навигации).

### Параллельная загрузка с asyncio.gather

```python
async def fetch_pages(urls: list[str]) -> list[dict[str, str]]:
    async with httpx.AsyncClient(...) as client:
        raw_results = await asyncio.gather(
            *[_fetch_one(client, url) for url in urls],
            return_exceptions=True,  # ← не падать при ошибке одного URL
        )
```

`asyncio.gather` запускает все HTTP-запросы **одновременно**.
Если загружать 5 страниц по 1 секунде каждая:
- Последовательно: 5 секунд
- Параллельно через `gather`: ~1 секунда

`return_exceptions=True` — важная деталь: если один URL недоступен,
остальные всё равно загрузятся. Без этого флага одна ошибка прерывала бы
весь вызов.

### Парсинг HTML с BeautifulSoup

```python
async def _fetch_one(client, url):
    response = await client.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Удаляем шум: скрипты, стили, навигацию
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    # Обрезаем: 3000 символов достаточно, больше перегружает контекст LLM
    if len(text) > 3_000:
        text = text[:3_000] + "\n... [truncated]"

    return {"url": url, "title": title, "content": text}
```

**Почему 3000 символов?** При 5 страницах это 15 000 символов ≈ 4000 токенов.
Если брать 8000 на страницу — 40 000 символов — контекст переполнится и LLM
не сможет сформировать ответ.

### Обработка ошибок

```python
for url, result in zip(urls, raw_results):
    if isinstance(result, Exception):
        output.append({"url": url, "error": str(result)})  # ← не падаем
    else:
        output.append(result)
```

Если URL недоступен (403, сетевая ошибка), инструмент возвращает
`{"url": ..., "error": "..."}` вместо того чтобы бросать исключение.
LLM увидит ошибку и просто пропустит этот источник.

---

## Инструмент 3: summarize_page

**Файл:** `tools/summarize.py`

### Что делает

Сжимает длинный текст до 200–400 слов, фокусируясь на ключевых фактах.
Используется когда страница слишком длинная для прямой передачи в контекст.

### Реализация

```python
SUMMARIZE_PROMPT = """\
Summarize the following content, focusing on: {focus}
Extract the most important facts, statistics, and insights.
Be concise — aim for 200-400 words.

Content:
{content}
"""

async def summarize_page(content: str, focus: str = "key findings") -> str:
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    message = await client.messages.create(
        model=settings.DEFAULT_MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
```

> **Текущее ограничение:** `summarize_page` использует Anthropic напрямую.
> Если вы используете другого провайдера без ключа Anthropic — инструмент
> вернёт ошибку. Оркестратор перехватит её и продолжит работу без суммаризации.

---

## Инструмент 4: write_report (терминальный)

**Файл:** `tools/report.py`

### Что делает

Принимает готовый Markdown-контент от LLM и оформляет его:
добавляет раздел со ссылками, считает слова, возвращает структурированный результат.

Это **терминальный инструмент** — его вызов сигнализирует оркестратору
завершить ReAct-цикл.

### Реализация

```python
@dataclass
class ReportResult:
    title: str
    content: str
    sources: list[dict[str, str]]
    word_count: int

async def write_report(title, content, sources=None) -> ReportResult:
    sources = sources or []

    # Добавляем раздел References если есть источники
    if sources:
        refs = "\n\n## References\n\n"
        for i, src in enumerate(sources, 1):
            refs += f"{i}. [{src['title']}]({src['url']})\n"
        content = content.rstrip() + refs

    word_count = len(content.split())

    return ReportResult(title=title, content=content,
                        sources=sources, word_count=word_count)
```

### Важный момент: LLM пишет контент, не мы

`write_report` не вызывает LLM для написания текста. LLM уже написала
содержимое отчёта в поле `content` при вызове инструмента. Наша функция
лишь форматирует готовый текст.

Это сделано намеренно — инструмент остаётся детерминированным (всегда
делает одно и то же для одних и тех же входных данных) и легко тестируемым.

---

## Соглашения при написании инструментов

### 1. Всегда async

```python
# ПРАВИЛЬНО:
async def my_tool(param: str) -> list[str]:
    result = await some_async_call()
    return result
```

Даже если внутри нет асинхронных операций — придерживайтесь `async def`,
чтобы реестр мог вызывать все инструменты единообразно.

### 2. Только ToolError при ошибках

```python
# НЕПРАВИЛЬНО — оркестратор упадёт:
raise ValueError("что-то пошло не так")

# ПРАВИЛЬНО — оркестратор перехватит и продолжит:
raise ToolError("что-то пошло не так", tool_name="my_tool")
```

### 3. Никакого print() — только structlog

```python
import structlog
log = structlog.get_logger(__name__)

# ПРАВИЛЬНО:
log.info("tool_done", results_count=len(results))

# НЕПРАВИЛЬНО — сломает Rich UI:
print(f"Найдено: {len(results)}")
```

---

## Что дальше

Инструменты написаны. Теперь нужно зарегистрировать их в каталоге,
чтобы LLM знала об их существовании: [07-registry.md](07-registry.md)
