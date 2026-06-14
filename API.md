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

## Пользователи

### Создать пользователя

```
POST /api/v1/users
```

**Тело запроса:**
```json
{
  "username": "alice"
}
```

**Ответ `201`:**
```json
{
  "external_id": "018f1a2b-3c4d-7e5f-8a9b-0c1d2e3f4a5b",
  "username": "alice",
  "created_at": "2026-06-15T12:00:00Z"
}
```

**Ответ `409`:** username уже занят.

---

### Получить пользователя

```
GET /api/v1/users/{external_id}
```

**Ответ `200`:** та же схема, что при создании.

**Ответ `404`:** пользователь не найден.

---

## Агенты

### Список доступных агентов

```
GET /api/v1/agents
```

Возвращает только те провайдеры, для которых задан API-ключ в конфигурации.

**Ответ `200`:**
```json
[
  { "provider": "openai",   "model": "gpt-5.4-mini" },
  { "provider": "claude",   "model": "claude-sonnet-4-6" }
]
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
  "created_at": "2026-06-15T12:00:00Z"
}
```

---

### Получить чат

```
GET /api/v1/chat/{external_id}
```

**Ответ `200`:** та же схема, что при создании.

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
- **Layer 2 (system instructions)** — открытые незакрытые цепочки других участников (с именами и временем)
- **Layer 3 (system instructions)** — семантически релевантные воспоминания из текущего и других чатов (требует настроенного embedding-бэкенда)

**Тело запроса:**
```json
{
  "content": "Текст сообщения",
  "user_id": "018f1a2b-3c4d-7e5f-8a9b-0c1d2e3f4a5b",
  "agent": "openai",
  "semantic_context": true
}
```

| Поле | Тип | Обязательное | Описание |
|---|---|---|---|
| `content` | string | да | Текст сообщения |
| `user_id` | UUID | нет | `external_id` пользователя. Включает цепочки и идентификацию в контексте агента |
| `agent` | enum | нет | Провайдер LLM: `openai`, `deepseek`, `claude`. По умолчанию: `openai` |
| `semantic_context` | bool | нет | Использовать семантический поиск по воспоминаниям. По умолчанию: `true`. Игнорируется, если embedding-бэкенд не настроен |

**Ответ `200`:**
```json
{
  "user_message": {
    "external_id": "018f...",
    "role": "user",
    "content": "Текст сообщения",
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

**Ответ `404`:** чат или пользователь не найден.

---

### Добавить сообщение в память

```
POST /api/v1/chat/{chat_external_id}/messages/memory
```

Сохраняет сообщение и немедленно генерирует эмбеддинг (если бэкенд настроен). Ответ от ИИ не генерируется. Используется для ручного пополнения долгосрочной памяти чата.

**Тело запроса:**
```json
{
  "content": "Пользователь предпочитает ответы на русском языке",
  "role": "user",
  "user_id": "018f..."
}
```

| Поле | Тип | Обязательное | Описание |
|---|---|---|---|
| `content` | string | да | Текст сообщения |
| `role` | enum | нет | `user` или `assistant`. По умолчанию: `user` |
| `user_id` | UUID | нет | `external_id` пользователя |

**Ответ `200`:** схема `MessageResponse`.

---

### Получить историю сообщений

```
GET /api/v1/chat/{chat_external_id}/messages
```

Возвращает до 200 сообщений в хронологическом порядке.

**Ответ `200`:**
```json
[
  {
    "external_id": "018f...",
    "role": "user",
    "content": "Привет",
    "sequence": 1,
    "created_at": "2026-06-15T12:00:00Z"
  }
]
```

---

## Цепочки сообщений (chains)

Когда в запросе указан `user_id`, сообщения автоматически группируются в цепочки — логические единицы одной мысли одного участника.

**Lifecycle цепочки:**

```
Первое сообщение пользователя  → создаётся цепочка (status: open)
Следующие сообщения            → присоединяются к той же цепочке
Пауза > CHAIN_GAP_SECONDS      → при следующем сообщении старая цепочка
                                  закрывается (status: closed), ставится
                                  в очередь на эмбеддинг
Воркер обрабатывает            → concat всех фрагментов → один вектор
                                  (status: embedded)
Брошенные цепочки              → воркер сам закрывает цепочки без активности
                                  дольше CHAIN_GAP_SECONDS
```

---

## Как агент видит контекст

```
[System Instructions]
You are a helpful assistant.

## Ongoing threads (other participants — may be incomplete thoughts)
[2026-06-15 12:01 UTC] bob: подожди
[2026-06-15 12:01 UTC] bob: я имею в виду что

## Long-term memory — this conversation
[2026-06-10 14:32 UTC] alice: как настроить базу данных?
[2026-06-10 14:33 UTC] assistant: нужно задать POSTGRES_* переменные

## Long-term memory — other conversations
The following context was retrieved from a DIFFERENT conversation.
Use it at your discretion. Decide independently whether to disclose
its origin to the user.

[2026-06-12 09:15 UTC] bob: мы используем PostgreSQL 16

[Messages array]
user: "предыдущий фрагмент цепочки alice"
user: "текущее сообщение alice"
```

Блоки **memory** появляются только если настроен embedding-бэкенд и `semantic_context: true`.
Блок **other conversations** появляется только если `CROSS_CHAT_SEMANTIC_LIMIT > 0`.

---

## Коды ошибок

| HTTP | Причина | Когда возникает |
|---|---|---|
| `401` | Неверный или отсутствующий `X-API-Key` | Все запросы без верного ключа |
| `404` | Ресурс не найден | Чат, пользователь не существует |
| `409` | Конфликт | Username уже занят |
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

## Эмбеддинги

Эмбеддинги используются для семантического поиска в долгосрочной памяти (Layer 3). Бэкенд выбирается переменной `EMBEDDING_BACKEND`.

### sentence-transformers (по умолчанию)

Запускается локально, не требует API-ключей. Модель скачивается с HuggingFace при первом старте и кешируется.

| Переменная | По умолчанию | Описание |
|---|---|---|
| `EMBEDDING_BACKEND` | `sentence_transformers` | Выбор бэкенда |
| `ST_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Модель (поддерживает русский язык) |
| `EMBEDDING_DIMENSIONS` | `384` | Размерность векторов |

Рекомендуемые модели:

| Модель | Dims | Языки | Размер |
|---|---|---|---|
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | 50+, включая RU | 470 MB |
| `all-MiniLM-L6-v2` | 384 | EN | 80 MB |
| `all-mpnet-base-v2` | 768 | EN | 420 MB |
| `multilingual-e5-large` | 1024 | 100+ | 1.1 GB |

> При смене модели с другой размерностью необходимо изменить `EMBEDDING_DIMENSIONS` и выполнить `alembic upgrade head` (существующие векторы будут удалены).

### OpenAI

| Переменная | По умолчанию | Описание |
|---|---|---|
| `EMBEDDING_BACKEND` | — | Установить в `openai` |
| `OPENAI_API_KEY` | — | Ключ OpenAI (обязательный для этого бэкенда) |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Модель |
| `EMBEDDING_DIMENSIONS` | `1536` | Установить в 1536 для `text-embedding-3-small` |

---

## Переменные окружения

| Переменная | По умолчанию | Описание |
|---|---|---|
| `API_KEY` | — | Ключ аутентификации для входящих запросов |
| `OPENAI_API_KEY` | — | Ключ OpenAI (нужен для агента `openai` или бэкенда `openai`) |
| `OPENAI_MODEL` | `gpt-5.4-mini` | Модель OpenAI |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Модель эмбеддингов OpenAI |
| `DEEPSEEK_API_KEY` | — | Ключ DeepSeek (опциональный) |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Модель DeepSeek |
| `ANTHROPIC_API_KEY` | — | Ключ Anthropic (опциональный) |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Модель Claude |
| `EMBEDDING_BACKEND` | `sentence_transformers` | Бэкенд эмбеддингов: `sentence_transformers` или `openai` |
| `ST_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Модель sentence-transformers |
| `EMBEDDING_DIMENSIONS` | `384` | Размерность векторов (должна совпадать с моделью) |
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
