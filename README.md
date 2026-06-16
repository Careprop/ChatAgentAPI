# ChatAgentAPI

Async FastAPI service that exposes a multi-provider chat agent with persistent sessions, semantic memory, and per-user token budgets. Backed by PostgreSQL + pgvector.

## Features

- **Multi-provider LLM** — OpenAI, Anthropic Claude, DeepSeek; switchable per message inside the same chat
- **Three-layer context** — direct history (Layer 1), open participant chains (Layer 2), semantic vector search (Layer 3)
- **Memory chains** — flood messages from `/memory` are grouped into chains and embedded on close
- **Semantic search** — pgvector similarity search across same-chat and cross-chat memories
- **Bot restart recovery** — `client_id` on users and `external_key` on chats allow stateless reconnect
- **Token budget** — 4-hour rolling token window per user with soft limit enforcement
- **Rate limiting** — per-IP and per-chat limits, per-user concurrency guard, per-chat concurrency cap

## Stack

| Component | Tech |
|---|---|
| API | FastAPI + uvicorn |
| ORM | SQLAlchemy 2.0 async |
| DB | PostgreSQL 16 + pgvector |
| Embeddings | sentence-transformers (via worker) or OpenAI |
| Migrations | Alembic |
| Rate limiting | slowapi |
| Python | 3.14+ (requires `uuid.uuid7`) |

## Quick start

```bash
cp .env.example .env   # fill in API_KEY + at least one LLM provider key
docker compose -f docker/docker-compose.yml up --build
```

The stack starts three containers: `agent_db` (Postgres), `agent_worker` (embedding service), `agent_api` (API on `:8000`).

Apply migrations on first run:

```bash
docker exec agent_api alembic upgrade head
```

API docs available at `http://localhost:8000/docs`.

## Configuration

Copy `.env.example` and set the required variables:

```env
# Required
API_KEY=your-inbound-auth-key
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=agent_lab
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# At least one provider
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=...

# Optional tuning
TOKEN_BUDGET=10000          # max tokens per user per 4-hour window
MAX_CHAT_CONCURRENT=5       # max simultaneous LLM calls per chat
CHAIN_GAP_SECONDS=5         # idle gap before a memory chain auto-closes
CONTEXT_DIRECT_LIMIT=20     # Layer 1: recent direct-call messages
CONTEXT_SEMANTIC_LIMIT=4    # Layer 3: same-chat memories
CROSS_CHAT_SEMANTIC_LIMIT=2 # Layer 3: cross-chat memories (0 = off)
```

Full variable reference in [API.md](API.md).

## Development

```bash
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000

# Migrations
alembic revision --autogenerate -m "describe change"
alembic upgrade head
alembic downgrade -1
```

## Architecture

```
app/
├── agent/
│   ├── backends/        # OpenAIBackend, ClaudeBackend, DeepSeekBackend
│   ├── embedding/       # EmbeddingBackend + pgvector store
│   └── schemas.py       # AgentMessage, AgentResponse, TokenUsage (provider-agnostic)
├── api/v1/
│   ├── routes/          # chat, message, user, agent
│   ├── schemas/         # Pydantic request/response models
│   └── dependencies/    # get_db, verify_api_key, rate_limit
├── db/
│   ├── models/          # Chat, Message, User, MessageChain, EmbeddingJob
│   └── mixins/          # TimestampMixin, SoftDeleteMixin
├── repositories/        # ChatRepository, MessageRepository, UserRepository, …
└── worker/              # Embedding job processor (runs as separate service)
```

**Key conventions:**
- All IDs in API responses are `uuid7` `external_id`s — internal integer PKs never leave the service
- Soft deletes: `deleted_at` timestamp; active-row queries filter `deleted_at IS NULL`
- New ORM models must be imported in `alembic/env.py` for autogenerate to pick them up

## API

Full endpoint reference in [API.md](API.md).

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/users` | Create user |
| `GET` | `/api/v1/users?client_id=` | Lookup by client_id (bot restart recovery) |
| `POST` | `/api/v1/chat` | Create chat |
| `GET` | `/api/v1/chat` | List chats (cursor pagination) |
| `DELETE` | `/api/v1/chat/{id}` | Soft delete chat |
| `POST` | `/api/v1/chat/{id}/messages` | Send message → LLM response |
| `POST` | `/api/v1/chat/{id}/messages/memory` | Save message without LLM call |
| `POST` | `/api/v1/chat/{id}/messages/memory/flush` | Close open chains immediately |
| `GET` | `/api/v1/chat/{id}/messages` | Message history (cursor pagination) |
| `GET` | `/api/v1/agents` | List configured providers |

All requests require `X-API-Key: <API_KEY>`.
