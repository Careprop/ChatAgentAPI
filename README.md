# ChatAgentAPI

Async REST API for a persistent, multi-participant chat agent backed by PostgreSQL. Built as a pet project to explore stateful LLM orchestration patterns: multi-provider routing, layered memory context, per-user token budgets, and safe concurrent access.

## Technical highlights

### Multi-provider LLM with a provider-agnostic interface
Three backends — OpenAI, Anthropic Claude, DeepSeek — all implement the same `AgentBackend` abstract class (`async generate(messages, ...)→ AgentResponse`). The provider is selected per-message, meaning clients can switch models mid-conversation without any server-side state migration. Adding a new provider is a single subclass.

Anthropic's tool-use model stops after emitting tool calls without generating a reply. The agent layer detects this and issues a second follow-up call (without tools) to obtain the text response, transparently to the caller.

### Three-layer memory context
Each `POST /messages` call assembles three independent context blocks before sending anything to the LLM:

| Layer | What | How |
|---|---|---|
| **L1 — recent history** | Token-budgeted message window | SQL window function `SUM(token_count) OVER (ORDER BY id DESC)` trims in-DB; no Python-side iteration over full history |
| **L3a — user facts** | Personal facts about the sender, scoped per chat | LLM tool call `save_fact`; stored as rows with `message_type='fact'`; separate "personality" per chat, no cross-chat leakage |
| **L3b — chat facts** | Shared facts about the group | LLM tool call `save_chat_fact`; visible to all participants of the same chat |

Facts are persisted autonomously by the LLM via tool calling — the client does not manage memory at all. Fact records carry `external_id` timestamps; the LLM can supersede (replace) outdated facts by ID, triggering a hard delete.

### Token budget
Per-user rolling 4-hour window. `check_token_budget` runs before the LLM call; `add_tokens` runs after. Soft limit: the request that pushes the balance negative is allowed through; subsequent requests are blocked until the window resets. `token_window_start` is initialized lazily on first use, so budget-less users generate no tracking state at all.

### Concurrency safety
Two independent guards:
- **Per-user lock** — `asyncio.Lock`-backed set; a user can only have one in-flight `send_message` at a time (`concurrent_request → 429`)
- **Per-chat cap** — counter map with configurable ceiling (`MAX_CHAT_CONCURRENT`); prevents a single group chat from monopolising the LLM under burst traffic (`chat_busy → 429`)

Both guards are released in a `finally` block regardless of LLM errors or timeouts.

### Two-transaction write pattern
`send_message` splits persistence across two commits:
1. **Commit 1** — user message saved immediately, before the LLM call. If the LLM times out, the user message is still on record.
2. **Commit 2** — facts extracted from tool calls + assistant reply saved together atomically.

### ID design
Every resource has two IDs: an autoincrement `integer` PK for internal joins and an `uuid7` `external_id` as the only identifier exposed over the API. Internal PKs never appear in responses.

`uuid7` requires Python 3.14+ (stdlib `uuid.uuid7`), which provides time-ordered UUIDs safe to use as cursor tokens for pagination.

### Soft deletes and partial indexes
Chats carry a `deleted_at` timestamp. Active-record queries filter `deleted_at IS NULL`; a partial unique index `WHERE deleted_at IS NULL` enforces uniqueness only on live rows, allowing the same `external_key` to be reused after deletion.

---

## Stack

| | |
|---|---|
| **Runtime** | Python 3.14 |
| **API** | FastAPI + Uvicorn |
| **ORM** | SQLAlchemy 2.0 async (`asyncpg`) |
| **DB** | PostgreSQL 16 |
| **Migrations** | Alembic |
| **Rate limiting** | slowapi |
| **Infra** | Docker Compose |

---

## Quick start

```bash
cp .env.example .env   # set API_KEY + at least one LLM provider key
docker compose -f docker/docker-compose.yml up --build
docker exec agent_api alembic upgrade head
```

API at `http://localhost:8000` · Swagger at `http://localhost:8000/docs`

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `API_KEY` | — | Inbound auth key (`X-API-Key` header) |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | — / `gpt-5.4-mini` | OpenAI provider |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | — / `claude-sonnet-4-6` | Anthropic provider |
| `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` | — / `deepseek-chat` | DeepSeek provider |
| `CONTEXT_HISTORY_TOKENS` | `4000` | L1 token budget (1 token ≈ 4 chars) |
| `CONTEXT_FACTS_LIMIT` | `10` | Max facts per user/chat included in context |
| `FACTS_PER_USER_LIMIT` | `20` | Hard cap on stored personal facts per user per chat |
| `CHAT_FACTS_PER_CHAT_LIMIT` | `20` | Hard cap on stored chat facts per chat |
| `MAX_CHAT_CONCURRENT` | `5` | Max simultaneous LLM calls per chat |
| `TOKEN_WINDOW_HOURS` | `4` | Rolling window duration for token budgets |

Full endpoint reference in [API.md](API.md).

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/users` | Create user with optional token budget |
| `GET` | `/api/v1/users?client_id=` | Lookup by client ID (stateless bot restart recovery) |
| `GET` | `/api/v1/users/{id}` | Get user by external ID |
| `POST` | `/api/v1/chat` | Create chat with optional `external_key` |
| `GET` | `/api/v1/chat` | List chats (cursor pagination via `before_id`) |
| `GET` | `/api/v1/chat/{id}` | Get chat |
| `DELETE` | `/api/v1/chat/{id}` | Soft delete chat |
| `POST` | `/api/v1/chat/{id}/messages` | Send message → LLM response + optional debug snapshot |
| `POST` | `/api/v1/chat/{id}/messages/memory` | Inject message into history without LLM call |
| `GET` | `/api/v1/chat/{id}/messages` | Message history (cursor pagination via `before_sequence`) |
| `GET` | `/api/v1/agents` | List configured LLM providers |

---

## Project structure

```
app/
├── agent/
│   ├── backends/      # OpenAIBackend, ClaudeBackend, DeepSeekBackend
│   ├── base.py        # AgentBackend abstract interface
│   ├── agent.py       # Tool orchestration + follow-up call logic
│   ├── tools.py       # save_fact / save_chat_fact tool definitions
│   └── schemas.py     # Provider-agnostic dataclasses (AgentMessage, AgentResponse)
├── api/v1/
│   ├── routes/        # chat, message, user, agent
│   ├── schemas/       # Pydantic request/response models
│   └── dependencies/  # get_db, verify_api_key, rate_limit
├── db/
│   ├── models/        # Chat, Message, User
│   └── mixins/        # TimestampMixin, SoftDeleteMixin
├── repositories/      # ChatRepository, MessageRepository, UserRepository
└── config/settings.py # Pydantic-settings from .env
```
