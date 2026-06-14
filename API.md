# ChatAgentAPI — документация

## Аутентификация

Все запросы требуют заголовок:

```
X-API-Key: <ваш ключ>
```

Значение задаётся переменной окружения `API_KEY`. При неверном ключе — `401 Unauthorized`.

---

## Базовый URL

```
http://localhost:8000
```

---

## Чаты

### Создать чат

```
POST /api/v1/chat
```

**Тело запроса:**
```json
{
  "title": "Название чата"
}
```

**Ответ `200`:**
```json
{
  "external_id": "018f1a2b-3c4d-7e5f-8a9b-0c1d2e3f4a5b",
  "title": "Название чата",
  "created_at": "2026-06-14T12:00:00Z"
}
```

---

### Получить чат

```
GET /api/v1/chat/{external_id}
```

**Параметры пути:**

| Параметр | Тип | Описание |
|---|---|---|
| `external_id` | UUID | Идентификатор чата |

**Ответ `200`:** — та же схема, что при создании.

**Ответ `404`:**
```json
{ "detail": "Chat not found" }
```

---

## Сообщения

### Отправить сообщение

```
POST /api/v1/chat/{chat_external_id}/messages
```

Отправляет пользовательское сообщение и получает ответ от агента. Контекст агенту передаётся в трёх слоях:

- **Layer 1 (messages array)** — фрагменты текущей цепочки участника + текущее сообщение
- **Layer 2 (system instructions)** — открытые незакрытые цепочки других участников (с метками и временем)
- **Layer 3 (system instructions)** — семантически релевантные воспоминания из прошлого чата

**Параметры пути:**

| Параметр | Тип | Описание |
|---|---|---|
| `chat_external_id` | UUID | Идентификатор чата |

**Тело запроса:**
```json
{
  "content": "Текст сообщения",
  "participant_id": "alice",
  "agent": "openai",
  "semantic_context": true
}
```

| Поле | Тип | Обязательное | Описание |
|---|---|---|---|
| `content` | string | да | Текст сообщения |
| `participant_id` | string | нет | Идентификатор участника (имя, UUID и т.д.). Используется для группировки сообщений в цепочки и gap-детекции. Без него цепочки не создаются |
| `agent` | enum | нет | Провайдер LLM: `openai`, `deepseek`, `claude`. По умолчанию: `openai` |
| `semantic_context` | bool | нет | Использовать семантический поиск по воспоминаниям. По умолчанию: `true` |

**Ответ `200`:**
```json
{
  "user_message": {
    "external_id": "018f...",
    "role": "user",
    "content": "Текст сообщения",
    "sequence": 1,
    "created_at": "2026-06-14T12:00:00Z"
  },
  "assistant_message": {
    "external_id": "018f...",
    "role": "assistant",
    "content": "Ответ агента",
    "sequence": 2,
    "created_at": "2026-06-14T12:00:01Z"
  }
}
```

---

### Добавить сообщение в память

```
POST /api/v1/chat/{chat_external_id}/messages/memory
```

Сохраняет сообщение в историю чата и немедленно генерирует для него эмбеддинг. Ответ от ИИ не генерируется. Используется для ручного пополнения долгосрочной памяти чата.

**Параметры пути:**

| Параметр | Тип | Описание |
|---|---|---|
| `chat_external_id` | UUID | Идентификатор чата |

**Тело запроса:**
```json
{
  "content": "Пользователь предпочитает ответы на русском языке",
  "role": "user"
}
```

| Поле | Тип | Обязательное | Описание |
|---|---|---|---|
| `content` | string | да | Текст сообщения |
| `role` | enum | нет | `user` или `assistant`. По умолчанию: `user` |

**Ответ `200`:** — схема `MessageResponse` (см. выше).

---

### Получить историю сообщений

```
GET /api/v1/chat/{chat_external_id}/messages
```

Возвращает до 200 сообщений в хронологическом порядке.

**Параметры пути:**

| Параметр | Тип | Описание |
|---|---|---|
| `chat_external_id` | UUID | Идентификатор чата |

**Ответ `200`:**
```json
[
  {
    "external_id": "018f...",
    "role": "user",
    "content": "Привет",
    "sequence": 1,
    "created_at": "2026-06-14T12:00:00Z"
  },
  {
    "external_id": "018f...",
    "role": "assistant",
    "content": "Здравствуйте!",
    "sequence": 2,
    "created_at": "2026-06-14T12:00:01Z"
  }
]
```

**Ответ `404`:**
```json
{ "detail": "Chat not found" }
```

---

## Цепочки сообщений (chains)

Когда в запросе указан `participant_id`, сообщения автоматически группируются в цепочки — логические единицы одной мысли одного участника.

**Lifecycle цепочки:**

```
Первое сообщение участника → создаётся цепочка (status: open)
Следующие сообщения       → присоединяются к той же цепочке
Пауза > chain_gap_seconds → при следующем сообщении цепочка закрывается
                             (status: closed) и ставится в очередь на эмбеддинг
Воркер обрабатывает       → конкатенация всех фрагментов → один вектор
                             (status: embedded)
```

**Gap-детекция:** порог паузы задаётся переменной окружения `CHAIN_GAP_SECONDS` (по умолчанию 5 секунд).

**Эмбеддинг цепочки:** при закрытии все фрагменты конкатенируются и эмбеддируются как одна семантическая единица. Вектор сохраняется на последнем сообщении цепочки и участвует в семантическом поиске при следующих запросах.

---

## Как агент видит контекст

При запросе генерации агенту передаётся:

```
[System Instructions]
You are a helpful assistant.

## Ongoing threads (other participants — may be incomplete thoughts)
These messages are from open chains that have not yet been resolved.
Be aware of them but do not treat them as part of the current dialogue.

[2026-06-15 12:01 UTC] bob: подожди
[2026-06-15 12:01 UTC] bob: я имею в виду что

## Long-term memory — this conversation
Relevant messages retrieved from earlier in this conversation.
Use them at your discretion — they are NOT part of the recent dialogue.

[2026-06-10 14:32 UTC] alice: как настроить базу данных?
[2026-06-10 14:33 UTC] assistant: нужно задать POSTGRES_* переменные

## Long-term memory — other conversations
The following context was retrieved from a DIFFERENT conversation.
Use it at your discretion. Decide independently whether to disclose
its origin to the user.

[2026-06-12 09:15 UTC] bob: мы используем PostgreSQL 16

[Messages array]
user: "предыдущий фрагмент текущей цепочки alice"
user: "текущее сообщение alice"   ← Layer 1
```

Блок **other conversations** появляется только если `CROSS_CHAT_SEMANTIC_LIMIT > 0` и семантический поиск нашёл релевантные сообщения из других чатов. Агент сам решает — раскрывать ли пользователю факт что информация из другого разговора.

---

## Коды ошибок

| HTTP | Причина | Когда возникает |
|---|---|---|
| `401` | Неверный или отсутствующий `X-API-Key` | Все запросы без верного ключа |
| `404` | Чат не найден | `GET /chat/{id}`, `POST/GET messages` |
| `422` | Невалидное тело запроса | Неверный тип поля, неизвестный `agent` или `role` |
| `429` | Rate limit провайдера | LLM вернул 429 |
| `502` | Ошибка на стороне провайдера | Неверный ключ, недоступная модель, сетевая ошибка |
| `503` | Провайдер не сконфигурирован | API-ключ для выбранного агента не задан в `.env` |
| `504` | Таймаут провайдера | LLM не ответил вовремя |

---

## Провайдеры агентов

| Значение | Провайдер | Переменные окружения |
|---|---|---|
| `openai` | OpenAI Responses API | `OPENAI_API_KEY`, `OPENAI_MODEL` (def. `gpt-5.4-mini`) |
| `deepseek` | DeepSeek Chat | `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` (def. `deepseek-chat`) |
| `claude` | Anthropic Claude | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` (def. `claude-sonnet-4-6`) |

---

## Переменные окружения

| Переменная | По умолчанию | Описание |
|---|---|---|
| `API_KEY` | — | Ключ аутентификации для входящих запросов |
| `OPENAI_API_KEY` | — | Ключ OpenAI (обязательный) |
| `OPENAI_MODEL` | `gpt-5.4-mini` | Модель OpenAI |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Модель эмбеддингов |
| `DEEPSEEK_API_KEY` | — | Ключ DeepSeek (опциональный) |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Модель DeepSeek |
| `ANTHROPIC_API_KEY` | — | Ключ Anthropic (опциональный) |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Модель Claude |
| `CHAIN_GAP_SECONDS` | `5` | Пауза в секундах для авто-закрытия цепочки |
| `EMBEDDING_WORKER_POLL_INTERVAL` | `2.0` | Интервал опроса очереди эмбеддингов (сек) |
| `EMBEDDING_JOB_MAX_ATTEMPTS` | `3` | Макс. попыток обработки одного job'а |
| `CONTEXT_SEMANTIC_LIMIT` | `4` | Макс. воспоминаний из текущего чата |
| `CROSS_CHAT_SEMANTIC_LIMIT` | `2` | Макс. воспоминаний из других чатов (0 = выключено) |
| `POSTGRES_HOST` | — | Хост PostgreSQL |
| `POSTGRES_PORT` | — | Порт PostgreSQL |
| `POSTGRES_DB` | — | Имя базы данных |
| `POSTGRES_USER` | — | Пользователь БД |
| `POSTGRES_PASSWORD` | — | Пароль БД |
