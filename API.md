# ChatAgentAPI

## Аутентификация

Все запросы требуют заголовок `X-API-Key: <ваш ключ>`. Значение задаётся переменной `API_KEY`. При неверном ключе — `401`.

---

## Архитектура памяти

При каждом вызове `POST /messages` агенту передаётся три слоя контекста:

| Слой | Что содержит |
|---|---|
| **L1 — история** | Последние сообщения чата, вписывающиеся в бюджет токенов (`CONTEXT_HISTORY_TOKENS`). Все участники, хронологический порядок. |
| **L3a — факты пользователя** | Личные факты об авторе текущего сообщения, сохранённые агентом через инструмент `save_fact`. Изолированы по чату — агент строит отдельную «личность» пользователя в каждом чате. |
| **L3b — факты чата** | Общие факты о чате/группе, сохранённые через `save_chat_fact`. Видны всем участникам чата. |

Агент сохраняет факты сам — клиенту не нужно ничего делать вручную.

---

## Пользователи

### `POST /api/v1/users`

Создать пользователя.

**Rate limit:** 60 req/мин (по IP).

```json
{
  "client_id": "tg:123456789",
  "display_name": "Ivan",
  "token_budget": 10000
}
```

| Поле | Тип | Описание |
|---|---|---|
| `client_id` | string | Уникальный идентификатор на стороне клиента (макс. 128 символов). Например: `"tg:123456789"` |
| `display_name` | string \| null | Имя для агента (макс. 256 символов) |
| `token_budget` | int \| null | Лимит токенов на 4-часовое окно. `null` — без ограничений |

**Ответ `201`:**

```json
{
  "external_id": "019ed1b8-...",
  "client_id": "tg:123456789",
  "display_name": "Ivan",
  "token_budget": 10000,
  "created_at": "2026-06-16T12:00:00Z"
}
```

`409` — `client_id` уже занят.

---

### `GET /api/v1/users?client_id=tg:123456789`

Найти пользователя по `client_id` — используется для восстановления состояния после перезапуска. Та же схема ответа. `404` — не найден.

---

### `GET /api/v1/users/{external_id}`

Та же схема ответа. `404` — не найден.

---

## Агенты

### `GET /api/v1/agents`

Возвращает провайдеры, для которых задан API-ключ.

```json
[
  { "provider": "openai",   "model": "gpt-5.4-mini" },
  { "provider": "claude",   "model": "claude-sonnet-4-6" },
  { "provider": "deepseek", "model": "deepseek-chat" }
]
```

| Значение `provider` | Переменные окружения |
|---|---|
| `openai` | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| `claude` | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` |
| `deepseek` | `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` |

Агент задаётся per-message — переключаться между провайдерами внутри одного чата безопасно, история общая.

---

## Чаты

### `POST /api/v1/chat`

**Rate limit:** 60 req/мин.

```json
{
  "title": "Мой чат",
  "external_key": "tg:-1001234567890"
}
```

| Поле | Тип | Описание |
|---|---|---|
| `title` | string | Название (макс. 128 символов) |
| `external_key` | string \| null | Произвольный ключ на стороне клиента (например, Telegram `chat_id`). Позволяет найти чат после перезапуска без хранения `external_id` |

**Ответ `201`:**

```json
{
  "external_id": "019ed1b4-...",
  "title": "Мой чат",
  "external_key": "tg:-1001234567890",
  "created_at": "2026-06-16T12:00:00Z"
}
```

`409` — `external_key` уже занят.

---

### `GET /api/v1/chat`

Список активных чатов, новые первыми. Cursor-based пагинация.

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| `limit` | int | `100` | Макс. 500 |
| `before_id` | UUID | — | Вернуть чаты старше этого `external_id` |
| `external_key` | string | — | Фильтр по ключу (возвращает 0 или 1 элемент) |

```
GET /api/v1/chat?external_key=tg:-1001234567890   # найти чат по Telegram chat_id
GET /api/v1/chat?limit=100&before_id=019ed1b4-... # следующая страница
```

---

### `GET /api/v1/chat/{external_id}`

Та же схема. `404` — не найден.

---

### `DELETE /api/v1/chat/{external_id}`

Мягкое удаление. **Rate limit:** 30 req/мин. `204 No Content`. `404` — не найден.

---

## Сообщения

### `POST /api/v1/chat/{chat_id}/messages`

Отправить сообщение агенту. Сохраняет пару user/assistant и возвращает ответ LLM.

**Rate limit:** 60 req/мин по IP + 60 req/мин на чат суммарно.

**Тело запроса:**

| Поле | Тип | По умолчанию | Описание |
|---|---|---|---|
| `content` | string | — | Текст сообщения (макс. 32 000 символов) |
| `user_id` | UUID \| null | `null` | `external_id` пользователя. Если задан — в контекст добавляются его личные факты |
| `display_name` | string \| null | `null` | Если передан и отличается от текущего — обновляет имя пользователя в БД |
| `agent` | enum | `openai` | Провайдер: `openai` / `claude` / `deepseek` |
| `metadata` | object \| null | `null` | Произвольные метаданные JSONB, сохраняются с user-сообщением |
| `debug` | bool | `false` | Добавить в ответ `debug_context` со снапшотом всех слоёв контекста |

**Ответ `200`:**

```json
{
  "user_message": {
    "external_id": "019ed1b8-...",
    "role": "user",
    "content": "Как дела?",
    "sequence": 5,
    "created_at": "2026-06-16T12:00:00Z",
    "metadata": null
  },
  "assistant_message": {
    "external_id": "019ed1b9-...",
    "role": "assistant",
    "content": "Всё отлично!",
    "sequence": 6,
    "created_at": "2026-06-16T12:00:01Z",
    "metadata": null
  },
  "token_usage": {
    "tokens_used": 1250,
    "token_budget": 10000,
    "tokens_remaining": 8750,
    "window_resets_at": "2026-06-16T16:00:00Z"
  },
  "debug_context": null
}
```

`token_usage` — `null` если `user_id` не передан или у пользователя нет бюджета. `tokens_remaining` может быть отрицательным: последний запрос пропускается (soft limit), но следующие блокируются до сброса окна.

**`debug_context` при `debug: true`:**

```json
{
  "debug_context": {
    "layer1_history": [
      { "role": "user",      "content": "[Ivan]: Привет", "sequence": 1 },
      { "role": "assistant", "content": "Здравствуй!",   "sequence": 2 }
    ],
    "layer3_user_facts": [
      { "role": "assistant", "content": "Любит кофе", "sequence": 10 }
    ],
    "layer3_chat_facts": [
      { "role": "assistant", "content": "Команда собирается по понедельникам в 10:00", "sequence": 11 }
    ]
  }
}
```

| Поле | Описание |
|---|---|
| `layer1_history` | История чата, переданная агенту. Сообщения от пользователей подписаны `[имя]:` |
| `layer3_user_facts` | Личные факты автора текущего сообщения |
| `layer3_chat_facts` | Общие факты чата |

---

### `POST /api/v1/chat/{chat_id}/messages/memory`

Добавить сообщение в историю чата **без вызова агента**. Используется для импорта сообщений других участников или исторических данных.

**Rate limit:** 300 req/мин.

| Поле | Тип | По умолчанию | Описание |
|---|---|---|---|
| `content` | string | — | Текст (макс. 32 000 символов) |
| `role` | enum | `user` | `user` / `assistant` |
| `user_id` | UUID \| null | `null` | Автор сообщения |
| `display_name` | string \| null | `null` | Если передан — обновляет имя пользователя |
| `metadata` | object \| null | `null` | Произвольные метаданные JSONB |

**Ответ `200`:** объект сообщения (та же схема что `user_message` выше).

---

### `GET /api/v1/chat/{chat_id}/messages`

История сообщений чата. Cursor-based пагинация от новых к старым.

**Rate limit:** 120 req/мин.

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| `limit` | int | `50` | Макс. 200 |
| `before_sequence` | int | — | Вернуть сообщения с `sequence < before_sequence` |

Без `before_sequence` — последние `limit` сообщений. Для листания: передавайте `sequence` первого элемента из предыдущей страницы.

---

## Коды ошибок

| HTTP | Причина |
|---|---|
| `401` | Неверный или отсутствующий `X-API-Key` |
| `404` | Ресурс не найден |
| `409` | `client_id` или `external_key` уже занят |
| `422` | Невалидное тело запроса |
| `429` | Rate limit или конкурентный запрос — см. ниже |
| `502` | Ошибка провайдера (неверный ключ, недоступная модель) |
| `503` | Провайдер не сконфигурирован (нет API-ключа) |
| `504` | Таймаут провайдера |

### Детализация 429

| `detail` | Причина | `Retry-After` |
|---|---|---|
| `"Rate limit exceeded: ..."` | Превышен rate limit по IP или по чату | секунды до сброса окна |
| `"concurrent_request"` | Для этого пользователя уже есть in-flight запрос | `1` |
| `"chat_busy"` | Превышен лимит параллельных запросов на чат | `1` |
| `"token_budget_exceeded"` | Исчерпан токенный бюджет пользователя | секунды до сброса 4-часового окна |

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
| `CONTEXT_HISTORY_TOKENS` | `4000` | Бюджет токенов для L1 истории (1 токен ≈ 4 символа) |
| `CONTEXT_FACTS_LIMIT` | `10` | Макс. фактов о пользователе / чате в контексте |
| `FACTS_PER_USER_LIMIT` | `20` | Макс. хранимых фактов на пользователя (старые удаляются) |
| `CHAT_FACTS_PER_CHAT_LIMIT` | `20` | Макс. хранимых фактов на чат (старые удаляются) |
| `MAX_CHAT_CONCURRENT` | `5` | Макс. параллельных LLM-запросов на один чат |
| `TOKEN_BUDGET` | `10000` | Дефолтный лимит токенов на пользователя за 4-часовое окно |
| `TOKEN_WINDOW_HOURS` | `4` | Длина окна сброса токенного бюджета (часы) |
| `POSTGRES_HOST` | — | Хост PostgreSQL |
| `POSTGRES_PORT` | — | Порт |
| `POSTGRES_DB` | — | База данных |
| `POSTGRES_USER` | — | Пользователь |
| `POSTGRES_PASSWORD` | — | Пароль |
