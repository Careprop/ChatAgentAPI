# ChatAgentAPI

## Аутентификация

Все запросы требуют заголовок `X-API-Key: <ваш ключ>`. Значение задаётся переменной `API_KEY`. При неверном ключе — `401`.

---

## Пользователи

### `POST /api/v1/users`

```json
{ "username": "alice" }
```

```json
{
  "external_id": "018f...",
  "username": "alice",
  "created_at": "2026-06-15T12:00:00Z"
}
```

`409` — username уже занят.

---

### `GET /api/v1/users/{external_id}`

Та же схема ответа. `404` — не найден.

---

## Агенты

### `GET /api/v1/agents`

Возвращает провайдеры, для которых задан API-ключ.

```json
[
  { "provider": "openai", "model": "gpt-5.4-mini" },
  { "provider": "claude", "model": "claude-sonnet-4-6" }
]
```

| Значение | Провайдер | Переменные окружения |
|---|---|---|
| `openai` | OpenAI Responses API | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| `deepseek` | DeepSeek Chat | `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` |
| `claude` | Anthropic Claude | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` |

---

## Чаты

### `POST /api/v1/chat`

```json
{ "title": "Название чата" }
```

```json
{
  "external_id": "018f...",
  "title": "Название чата",
  "created_at": "2026-06-15T12:00:00Z"
}
```

---

### `GET /api/v1/chat/{external_id}`

Та же схема. `404` — не найден.

---

## Сообщения

### `POST /api/v1/chat/{chat_external_id}/messages`

Прямое обращение к агенту. Сохраняет пару user/assistant сообщений и возвращает ответ LLM. Агенту передаётся история предыдущих обращений через этот же endpoint, открытые цепочки участников (из `/memory`) и семантические воспоминания.

**Тело запроса:**

| Поле | Тип | Обязательное | Описание |
|---|---|---|---|
| `content` | string | да | Текст сообщения |
| `user_id` | UUID | нет | `external_id` пользователя |
| `agent` | enum | нет | `openai` / `deepseek` / `claude`. По умолчанию: `openai` |
| `semantic_context` | bool | нет | Семантический поиск. По умолчанию: `true` |

**Ответ `200`:**

```json
{
  "user_message": {
    "external_id": "018f...",
    "role": "user",
    "content": "Текст",
    "sequence": 1,
    "created_at": "2026-06-15T12:00:00Z"
  },
  "assistant_message": {
    "external_id": "018f...",
    "role": "assistant",
    "content": "Ответ агента",
    "sequence": 2,
    "created_at": "2026-06-15T12:00:01Z"
  }
}
```

---

### `POST /api/v1/chat/{chat_external_id}/messages/memory`

Сохраняет сообщение без вызова агента. Для сообщений пользователя с `user_id` автоматически ведётся цепочка: несколько сообщений подряд объединяются в одну логическую единицу и встраиваются в векторное хранилище воркером при закрытии цепочки. Используется для сохранения флуда и истории чата из внешних источников.

| Поле | Тип | Обязательное | Описание |
|---|---|---|---|
| `content` | string | да | Текст |
| `role` | enum | нет | `user` (по умолчанию) / `assistant` |
| `user_id` | UUID | нет | `external_id` пользователя |

**Ответ `200`:** `MessageResponse` (схема как у одного сообщения выше).

---

### `GET /api/v1/chat/{chat_external_id}/messages`

Возвращает до 200 сообщений в хронологическом порядке.

---

## Коды ошибок

| HTTP | Причина |
|---|---|
| `401` | Неверный или отсутствующий `X-API-Key` |
| `404` | Чат или пользователь не найден |
| `409` | Username уже занят |
| `422` | Невалидное тело запроса |
| `429` | Rate limit провайдера |
| `502` | Ошибка провайдера (неверный ключ, недоступная модель) |
| `503` | Провайдер не сконфигурирован |
| `504` | Таймаут провайдера |

---

## Переменные окружения

| Переменная | По умолчанию | Описание |
|---|---|---|
| `API_KEY` | — | Ключ аутентификации |
| `OPENAI_API_KEY` | — | Ключ OpenAI |
| `OPENAI_MODEL` | `gpt-5.4-mini` | Модель OpenAI |
| `DEEPSEEK_API_KEY` | — | Ключ DeepSeek |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Модель DeepSeek |
| `ANTHROPIC_API_KEY` | — | Ключ Anthropic |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Модель Claude |
| `EMBEDDING_BACKEND` | `sentence_transformers` | `sentence_transformers` или `openai` |
| `ST_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Модель sentence-transformers |
| `EMBEDDING_DIMENSIONS` | `384` | Размерность векторов |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Модель эмбеддингов OpenAI |
| `CHAIN_GAP_SECONDS` | `5` | Пауза для авто-закрытия цепочки (сек) |
| `CONTEXT_SEMANTIC_LIMIT` | `4` | Макс. воспоминаний из текущего чата |
| `CROSS_CHAT_SEMANTIC_LIMIT` | `2` | Макс. воспоминаний из других чатов (0 = выключено) |
| `EMBEDDING_WORKER_POLL_INTERVAL` | `2.0` | Интервал опроса воркера (сек) |
| `EMBEDDING_JOB_MAX_ATTEMPTS` | `3` | Макс. попыток обработки job |
| `POSTGRES_HOST` | — | Хост PostgreSQL |
| `POSTGRES_PORT` | — | Порт |
| `POSTGRES_DB` | — | База данных |
| `POSTGRES_USER` | — | Пользователь |
| `POSTGRES_PASSWORD` | — | Пароль |
