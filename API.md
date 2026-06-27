# API Reference

## Authentication

All requests require the header `X-API-Key: <your key>`. The value is set via the `API_KEY` environment variable. Wrong or missing key returns `401`.

---

## Memory architecture

Every `POST /messages` call assembles three context layers before sending anything to the LLM:

| Layer | Contents |
|---|---|
| **L1 — history** | Recent messages from this chat that fit within the token budget (`CONTEXT_HISTORY_TOKENS`). All participants, chronological order. |
| **L3a — user facts** | Personal facts about the author of the current message, saved by the agent via the `save_fact` tool. Scoped per chat — the agent builds a separate "personality" for each user in each chat. |
| **L3b — chat facts** | Shared facts about the chat or group, saved via `save_chat_fact`. Visible to all participants of the same chat. |

The agent saves facts autonomously — the client does not manage memory at all.

---

## Users

### `POST /api/v1/users`

Create a user.

**Rate limit:** 60 req/min (by IP).

```json
{
  "client_id": "tg:123456789",
  "display_name": "Ivan",
  "token_budget": 10000
}
```

| Field | Type | Description |
|---|---|---|
| `client_id` | string | Unique client-side identifier (max 128 chars). Example: `"tg:123456789"` |
| `display_name` | string \| null | Name shown to the agent (max 256 chars) |
| `token_budget` | int \| null | Max tokens per 4-hour rolling window. `null` — unlimited |

**Response `201`:**

```json
{
  "external_id": "019ed1b8-...",
  "client_id": "tg:123456789",
  "display_name": "Ivan",
  "token_budget": 10000,
  "created_at": "2026-06-16T12:00:00Z"
}
```

`409` — `client_id` already taken.

---

### `GET /api/v1/users?client_id=tg:123456789`

Find a user by `client_id` — used to restore state after a bot restart. Same response schema. `404` — not found.

---

### `GET /api/v1/users/{external_id}`

Same response schema. `404` — not found.

---

## Agents

### `GET /api/v1/agents`

Returns the providers for which an API key is configured.

```json
[
  { "provider": "openai",   "model": "gpt-5.4-mini" },
  { "provider": "claude",   "model": "claude-sonnet-4-6" },
  { "provider": "deepseek", "model": "deepseek-chat" }
]
```

| `provider` value | Environment variables |
|---|---|
| `openai` | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| `claude` | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` |
| `deepseek` | `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` |

The provider is selected per-message — switching between providers within the same chat is safe, history is shared.

---

## Chats

### `POST /api/v1/chat`

**Rate limit:** 60 req/min.

```json
{
  "title": "My chat",
  "external_key": "tg:-1001234567890"
}
```

| Field | Type | Description |
|---|---|---|
| `title` | string | Chat name (max 128 chars) |
| `external_key` | string \| null | Arbitrary client-side key (e.g. Telegram `chat_id`). Allows finding the chat after a restart without storing `external_id` |

**Response `201`:**

```json
{
  "external_id": "019ed1b4-...",
  "title": "My chat",
  "external_key": "tg:-1001234567890",
  "created_at": "2026-06-16T12:00:00Z"
}
```

`409` — `external_key` already in use.

---

### `GET /api/v1/chat`

List active chats, newest first. Cursor-based pagination.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `limit` | int | `100` | Max 500 |
| `before_id` | UUID | — | Return chats older than this `external_id` |
| `external_key` | string | — | Filter by key (returns 0 or 1 result) |

```
GET /api/v1/chat?external_key=tg:-1001234567890   # find chat by Telegram chat_id
GET /api/v1/chat?limit=100&before_id=019ed1b4-... # next page
```

---

### `GET /api/v1/chat/{external_id}`

Same schema. `404` — not found.

---

### `DELETE /api/v1/chat/{external_id}`

Soft delete. **Rate limit:** 30 req/min. `204 No Content`. `404` — not found.

---

## Messages

### `POST /api/v1/chat/{chat_id}/messages`

Send a message to the agent. Saves the user/assistant pair and returns the LLM reply.

**Rate limit:** 60 req/min by IP + 60 req/min per chat.

**Request body:**

| Field | Type | Default | Description |
|---|---|---|---|
| `content` | string | — | Message text (max 32 000 chars) |
| `user_id` | UUID \| null | `null` | User `external_id`. If set — personal facts are included in context |
| `display_name` | string \| null | `null` | If provided and different from stored — updates the user's display name in DB |
| `agent` | enum | `openai` | Provider: `openai` / `claude` / `deepseek` |
| `metadata` | object \| null | `null` | Arbitrary JSONB metadata, saved with the user message |
| `debug` | bool | `false` | Include `debug_context` in the response with a per-layer context snapshot |

**Response `200`:**

```json
{
  "user_message": {
    "external_id": "019ed1b8-...",
    "role": "user",
    "content": "How are you?",
    "sequence": 5,
    "created_at": "2026-06-16T12:00:00Z",
    "metadata": null
  },
  "assistant_message": {
    "external_id": "019ed1b9-...",
    "role": "assistant",
    "content": "All good!",
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

`token_usage` is `null` if `user_id` is not provided or the user has no budget. `tokens_remaining` can be negative: the request that crosses the limit is allowed through (soft limit), but subsequent ones are blocked until the window resets.

**`debug_context` when `debug: true`:**

```json
{
  "debug_context": {
    "layer1_history": [
      { "role": "user",      "content": "[Ivan]: Hello", "sequence": 1 },
      { "role": "assistant", "content": "Hi there!",     "sequence": 2 }
    ],
    "layer3_user_facts": [
      { "role": "assistant", "content": "Likes coffee", "sequence": 10 }
    ],
    "layer3_chat_facts": [
      { "role": "assistant", "content": "Team meets on Mondays at 10:00", "sequence": 11 }
    ]
  }
}
```

| Field | Description |
|---|---|
| `layer1_history` | Chat history passed to the agent. User messages are prefixed with `[name]:` |
| `layer3_user_facts` | Personal facts about the current message author |
| `layer3_chat_facts` | Shared facts for this chat |

---

### `POST /api/v1/chat/{chat_id}/messages/memory`

Add a message to chat history **without calling the LLM**. Used to import messages from other participants or historical data.

**Rate limit:** 300 req/min.

| Field | Type | Default | Description |
|---|---|---|---|
| `content` | string | — | Text (max 32 000 chars) |
| `role` | enum | `user` | `user` / `assistant` |
| `user_id` | UUID \| null | `null` | Message author |
| `display_name` | string \| null | `null` | If provided — updates the user's display name |
| `metadata` | object \| null | `null` | Arbitrary JSONB metadata |

**Response `200`:** message object (same schema as `user_message` above).

---

### `GET /api/v1/chat/{chat_id}/messages`

Chat message history. Cursor-based pagination, newest first.

**Rate limit:** 120 req/min.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `limit` | int | `50` | Max 200 |
| `before_sequence` | int | — | Return messages with `sequence < before_sequence` |

Without `before_sequence` — returns the latest `limit` messages. To paginate: pass the `sequence` of the first element from the previous page.

---

## Error codes

| HTTP | Reason |
|---|---|
| `401` | Invalid or missing `X-API-Key` |
| `404` | Resource not found |
| `409` | `client_id` or `external_key` already taken |
| `422` | Invalid request body |
| `429` | Rate limit or concurrent request — see below |
| `502` | Provider error (invalid key, unavailable model) |
| `503` | Provider not configured (no API key set) |
| `504` | Provider timeout |

### 429 detail breakdown

| `detail` | Reason | `Retry-After` |
|---|---|---|
| `"Rate limit exceeded: ..."` | IP or per-chat rate limit hit | seconds until window resets |
| `"concurrent_request"` | This user already has an in-flight request | `1` |
| `"chat_busy"` | Per-chat concurrent request cap exceeded | `1` |
| `"token_budget_exceeded"` | User's token budget exhausted | seconds until 4-hour window resets |

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `API_KEY` | — | Inbound authentication key |
| `OPENAI_API_KEY` | — | OpenAI key |
| `OPENAI_MODEL` | `gpt-5.4-mini` | OpenAI model |
| `OPENAI_MAX_TOKENS` | `8192` | Max output tokens for OpenAI |
| `DEEPSEEK_API_KEY` | — | DeepSeek key |
| `DEEPSEEK_MODEL` | `deepseek-chat` | DeepSeek model |
| `DEEPSEEK_MAX_TOKENS` | `8192` | Max output tokens for DeepSeek |
| `ANTHROPIC_API_KEY` | — | Anthropic key |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Claude model |
| `ANTHROPIC_MAX_TOKENS` | `8192` | Max output tokens for Claude |
| `CONTEXT_HISTORY_TOKENS` | `4000` | L1 token budget (1 token ≈ 4 chars) |
| `CONTEXT_FACTS_LIMIT` | `10` | Max facts per user / per chat included in context |
| `FACTS_PER_USER_LIMIT` | `20` | Hard cap on stored personal facts per user per chat (oldest deleted when exceeded) |
| `CHAT_FACTS_PER_CHAT_LIMIT` | `20` | Hard cap on stored chat facts per chat (oldest deleted when exceeded) |
| `MAX_CHAT_CONCURRENT` | `5` | Max simultaneous LLM requests per chat |
| `TOKEN_WINDOW_HOURS` | `4` | Rolling window duration for per-user token budgets (hours) |
| `POSTGRES_HOST` | — | PostgreSQL host |
| `POSTGRES_PORT` | — | PostgreSQL port |
| `POSTGRES_DB` | — | Database name |
| `POSTGRES_USER` | — | Database user |
| `POSTGRES_PASSWORD` | — | Database password |
