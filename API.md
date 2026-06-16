# ChatAgentAPI

## Аутентификация

Все запросы требуют заголовок `X-API-Key: <ваш ключ>`. Значение задаётся переменной `API_KEY`. При неверном ключе — `401`.

Rate limiting (по IP): `POST /messages` — 60 req/мин, `POST /memory` — 300/мин, `POST /chat` и `POST /users` — 60/мин, `DELETE /chat` — 30/мин, `GET /messages` — 120/мин, `POST /memory/flush` — 60/мин. Дополнительно: `POST /messages` — 60 req/мин на чат суммарно со всех IP.

---

## Пользователи

### `POST /api/v1/users`

```json
{ "client_id": "tg:123456789", "display_name": "Ivan" }
```

| Поле | Тип | Описание |
|---|---|---|
| `client_id` | string | Уникальный идентификатор, задаётся клиентом (макс. 128 символов). Например: `"tg:123456789"` |
| `display_name` | string \| null | Имя для агента (макс. 256 символов). Опциональное |

**Ответ `201`:**

```json
{
  "external_id": "018f...",
  "client_id": "tg:123456789",
  "display_name": "Ivan",
  "created_at": "2026-06-16T12:00:00Z"
}
```

`409` — `client_id` уже занят.

---

### `GET /api/v1/users?client_id=tg:123456789`

Поиск по `client_id` — используется для восстановления состояния бота после перезапуска. Та же схема ответа. `404` — не найден.

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

Агент задаётся per-message и не влияет на хранимую историю — переключаться между провайдерами внутри одного чата безопасно.

---

## Чаты

### `POST /api/v1/chat`

```json
{
  "title": "Название чата",
  "external_key": "tg:123456789"
}
```

`external_key` — необязательный уникальный ключ, контролируемый клиентом (например, `"tg:<telegram_chat_id>"`). Позволяет боту найти чат после перезапуска без хранения `external_id` на своей стороне.

**Ответ `201`:**

```json
{
  "external_id": "018f...",
  "title": "Название чата",
  "external_key": "tg:123456789",
  "created_at": "2026-06-15T12:00:00Z"
}
```

`409` — `external_key` уже занят.

---

### `GET /api/v1/chat`

Список активных чатов, новые первыми. Поддерживает cursor-based пагинацию и поиск по `external_key`.

**Query params:**

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| `limit` | int | `100` | Макс. 500 |
| `before_id` | UUID | нет | Курсор: вернуть чаты старше этого `external_id` |
| `external_key` | string | нет | Фильтр по ключу (уникальный — возвращает 0 или 1 элемент) |

**Пример пагинации:**
```
GET /chat?limit=100                          # первая страница
GET /chat?limit=100&before_id=<last_ext_id>  # следующая страница
```

**Поиск чата по Telegram chat_id после рестарта:**
```
GET /chat?external_key=tg:123456789  # [] если не существует, [chat] если есть
```

Ответ: массив объектов схемы чата.

---

### `GET /api/v1/chat/{external_id}`

Та же схема. `404` — не найден.

---

### `DELETE /api/v1/chat/{external_id}`

Мягкое удаление. `204 No Content`. `404` — не найден.

---

## Сообщения

### `POST /api/v1/chat/{chat_external_id}/messages`

Прямое обращение к агенту. Сохраняет пару user/assistant сообщений и возвращает ответ LLM.

Агенту передаётся:
- **Layer 1** — последние N обращений через этот же endpoint (прямая история)
- **Layer 2** — открытые цепочки участников из `/memory`
- **Layer 3** — семантически релевантные воспоминания и факты о пользователе (pgvector)

Одновременно допускается только один in-flight запрос на одного идентифицированного пользователя (`429 concurrent_request`). Суммарно на чат — не более `MAX_CHAT_CONCURRENT` параллельных запросов (`429 chat_busy`).

**Тело запроса:**

| Поле | Тип | По умолчанию | Описание |
|---|---|---|---|
| `content` | string | — | Текст (обязательное, макс. 32 000 символов) |
| `user_id` | UUID | `null` | `external_id` пользователя |
| `display_name` | string \| null | `null` | Если передан — тихо обновляет имя пользователя в БД |
| `agent` | enum | `openai` | `openai` / `deepseek` / `claude` |
| `semantic_context` | bool | `true` | Включить Layer 3 (семантический поиск) |
| `cross_chat_context` | bool | `true` | Включить семантику из других чатов (в рамках Layer 3) |
| `metadata` | object | `null` | Произвольные метаданные JSONB, например `{"telegram_message_id": 123}` |
| `debug` | bool | `false` | Вернуть `debug_context` с содержимым всех слоёв контекста, переданных агенту |

**Ответ `200`:**

```json
{
  "user_message": {
    "external_id": "018f...",
    "role": "user",
    "content": "Текст",
    "sequence": 1,
    "created_at": "2026-06-15T12:00:00Z",
    "metadata": {"telegram_message_id": 123}
  },
  "assistant_message": {
    "external_id": "018f...",
    "role": "assistant",
    "content": "Ответ агента",
    "sequence": 2,
    "created_at": "2026-06-15T12:00:01Z",
    "metadata": null
  },
  "token_usage": {
    "tokens_used": 1250,
    "token_budget": 10000,
    "tokens_remaining": 8750,
    "window_resets_at": "2026-06-16T16:00:00Z"
  }
}
```

`token_usage` — `null` если у пользователя нет бюджета или `user_id` не передан. `tokens_remaining` может быть отрицательным, если последний запрос превысил остаток (soft limit — запрос пропускается, но последующие блокируются).

Если `debug: true`, ответ содержит дополнительное поле `debug_context`:

```json
{
  "debug_context": {
    "layer1_direct_history": [
      { "role": "user", "content": "Привет", "sequence": 1 },
      { "role": "assistant", "content": "Здравствуй!", "sequence": 2 }
    ],
    "layer2_open_chains": [
      {
        "participant": "Анна",
        "messages": [
          { "role": "user", "content": "...", "sequence": 5 }
        ]
      }
    ],
    "layer3_facts": [
      { "role": "assistant", "content": "Пользователь говорит по-русски", "sequence": 3 }
    ],
    "layer3_same_chat_memories": [],
    "layer3_cross_chat_memories": []
  }
}
```

| Поле | Описание |
|---|---|
| `layer1_direct_history` | Прямые обращения к агенту (Layer 1) — то, что идёт в `messages[]` агенту |
| `layer2_open_chains` | Открытые цепочки от других участников (Layer 2) |
| `layer3_facts` | Факты о пользователе, найденные семантическим поиском (Layer 3) |
| `layer3_same_chat_memories` | Релевантные воспоминания из текущего чата (Layer 3) |
| `layer3_cross_chat_memories` | Релевантные воспоминания из других чатов (Layer 3) |

`debug_context: null` когда `debug: false` (по умолчанию). В production передавать `debug: true` не рекомендуется — раскрывает внутренний контекст агента.

---

### `POST /api/v1/chat/{chat_external_id}/messages/memory`

Сохраняет сообщение без вызова агента. Для сообщений пользователя с `user_id` автоматически ведётся цепочка: несколько сообщений подряд объединяются в одну логическую единицу и встраиваются в векторное хранилище воркером при закрытии цепочки.

| Поле | Тип | По умолчанию | Описание |
|---|---|---|---|
| `content` | string | — | Текст (обязательное, макс. 32 000 символов) |
| `role` | enum | `user` | `user` / `assistant` |
| `user_id` | UUID | `null` | `external_id` пользователя |
| `display_name` | string \| null | `null` | Если передан — тихо обновляет имя пользователя в БД |
| `metadata` | object | `null` | Произвольные метаданные JSONB |

**Ответ `200`:** `MessageResponse` (схема как у одного сообщения выше).

---

### `POST /api/v1/chat/{chat_external_id}/messages/memory/flush`

Явно закрывает открытые цепочки, не дожидаясь таймаута `CHAIN_GAP_SECONDS`. Позволяет немедленно поставить цепочки в очередь на эмбеддинг.

**Тело запроса:**

| Поле | Тип | Описание |
|---|---|---|
| `user_id` | UUID \| null | Конкретный пользователь. Если `null` — закрывает **все** открытые цепочки в чате (batch flush) |

**Ответ `200`:**

```json
{ "count": 3 }
```

`count: 0` — если открытых цепочек не было. Уже закрытые цепочки игнорируются — endpoint идемпотентен.

---

### `GET /api/v1/chat/{chat_external_id}/messages`

История сообщений. Cursor-based пагинация: запросы идут от новых к старым через `before_sequence`.

**Query params:**

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| `limit` | int | `50` | Макс. 200 |
| `before_sequence` | int | нет | Вернуть сообщения с `sequence < before_sequence` |

Без `before_sequence` — возвращает последние `limit` сообщений.
Для загрузки предыдущих: передавайте `before_sequence` равным `sequence` первого сообщения из предыдущего ответа.

---

## Коды ошибок

| HTTP | Причина |
|---|---|
| `401` | Неверный или отсутствующий `X-API-Key` |
| `404` | Чат, пользователь или ресурс не найден |
| `409` | `client_id` или `external_key` уже занят |
| `422` | Невалидное тело запроса (превышена длина, неверный формат) |
| `429` | Rate limit или параллельный запрос — см. ниже |
| `502` | Ошибка провайдера (неверный ключ, недоступная модель) |
| `503` | Провайдер не сконфигурирован |
| `504` | Таймаут провайдера |

### Различение причин 429

| Источник | `detail` | `Retry-After` |
|---|---|---|
| Rate limit (IP или чат) | `"Rate limit exceeded: ..."` | есть (секунды до сброса окна) |
| Один юзер — два запроса подряд | `"concurrent_request"` | `1` |
| Чат перегружен (> `MAX_CHAT_CONCURRENT`) | `"chat_busy"` | `1` |
| Токенный бюджет исчерпан | `"token_budget_exceeded"` | секунды до сброса 4-часового окна |

Все значения — строки. `Retry-After` присутствует во всех трёх случаях — клиент всегда может опираться на него для backoff.

### Удаление пользователей

`DELETE /api/v1/users` **отсутствует намеренно** — пользователь является anchor для фактов, цепочек и истории. Удаление требует каскадной очистки всех связанных данных, что является отдельной функцией (GDPR-сценарий).

---

## Переменные окружения

| Переменная | По умолчанию | Описание |
|---|---|---|
| `API_KEY` | — | Ключ аутентификации |
| `OPENAI_API_KEY` | — | Ключ OpenAI |
| `OPENAI_MODEL` | `gpt-5.4-mini` | Модель OpenAI |
| `OPENAI_MAX_TOKENS` | `8192` | Лимит токенов ответа OpenAI |
| `DEEPSEEK_API_KEY` | — | Ключ DeepSeek |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Модель DeepSeek |
| `DEEPSEEK_MAX_TOKENS` | `8192` | Лимит токенов ответа DeepSeek |
| `ANTHROPIC_API_KEY` | — | Ключ Anthropic |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Модель Claude |
| `ANTHROPIC_MAX_TOKENS` | `8192` | Лимит токенов ответа Claude |
| `EMBEDDING_BACKEND` | `sentence_transformers` | `sentence_transformers` или `openai` |
| `WORKER_EMBED_URL` | `http://worker:8001` | URL embedding-сервиса воркера |
| `ST_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Модель sentence-transformers |
| `EMBEDDING_DIMENSIONS` | `384` | Размерность векторов |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Модель эмбеддингов OpenAI |
| `CHAIN_GAP_SECONDS` | `5` | Пауза для авто-закрытия цепочки (сек) |
| `MAX_CHAIN_AGE_SECONDS` | `300` | Открытые цепочки старше этого (сек) исключаются из Layer 2 контекста |
| `MAX_CHAT_CONCURRENT` | `5` | Макс. одновременных LLM-запросов на один чат |
| `TOKEN_BUDGET` | `10000` | Макс. токенов на пользователя за 4-часовое окно (будущее: per-user override) |
| `TOKEN_WINDOW_HOURS` | `4` | Длина окна сброса токенного бюджета (часы) |
| `CONTEXT_DIRECT_LIMIT` | `20` | Макс. сообщений в Layer 1 (прямая история) |
| `CONTEXT_SEMANTIC_LIMIT` | `4` | Макс. воспоминаний из текущего чата (Layer 3) |
| `CROSS_CHAT_SEMANTIC_LIMIT` | `2` | Макс. воспоминаний из других чатов (0 = выключено) |
| `CONTEXT_FACTS_LIMIT` | `3` | Макс. фактов о пользователе в контексте |
| `FACT_DEDUP_THRESHOLD` | `0.15` | Cosine distance: факты ближе порога считаются дубликатами |
| `FACTS_PER_USER_LIMIT` | `20` | Макс. фактов на пользователя на чат (старые удаляются) |
| `WORKER_API_KEY` | `API_KEY` | Ключ для API→воркер вызовов (по умолчанию = `API_KEY`) |
| `EMBEDDING_WORKER_POLL_INTERVAL` | `2.0` | Интервал опроса воркера (сек) |
| `EMBEDDING_JOB_MAX_ATTEMPTS` | `3` | Макс. попыток обработки embedding job |
| `POSTGRES_HOST` | — | Хост PostgreSQL |
| `POSTGRES_PORT` | — | Порт |
| `POSTGRES_DB` | — | База данных |
| `POSTGRES_USER` | — | Пользователь |
| `POSTGRES_PASSWORD` | — | Пароль |
