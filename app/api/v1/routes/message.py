import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.embedding.backends.openai import OpenAIEmbeddingBackend
from app.agent.embedding.base import should_embed
from app.agent.embedding.stores.pgvector import PgvectorStore
from app.agent.schemas import AgentMessage, Role
from app.api.v1.dependencies.agent import get_agent
from app.api.v1.dependencies.auth import verify_api_key
from app.api.v1.dependencies.db import get_db
from app.api.v1.dependencies.embedding import get_embedding_backend, get_embedding_store
from app.api.v1.schemas.message import AddMemoryRequest, MessageResponse, SendMessageRequest, SendMessageResponse
from app.config.settings import settings
from app.db.models.chain import MessageChain
from app.db.models.message import Message
from app.db.models.user import User
from app.repositories.chain import ChainRepository
from app.repositories.chat import ChatRepository
from app.repositories.embedding_job import EmbeddingJobRepository
from app.repositories.message import MessageRepository
from app.repositories.user import UserRepository
from app.worker.embedding import flush_pending_for_chat

router = APIRouter(
    prefix="/api/v1/chat/{chat_external_id}/messages",
    tags=["messages"],
)


# ---------------------------------------------------------------------------
# Context formatting helpers
# ---------------------------------------------------------------------------

def _label(user: User | None, role: str) -> str:
    return user.username if user else role


def _format_open_chains_block(
    chains: list[MessageChain], current_chain_id: int | None
) -> str | None:
    other = [c for c in chains if c.id != current_chain_id]
    if not other:
        return None
    lines = [
        "## Ongoing threads (other participants — may be incomplete thoughts)",
        "These messages are from open chains that have not yet been resolved.",
        "Be aware of them but do not treat them as part of the current dialogue.",
        "",
    ]
    for chain in other:
        label = chain.user.username if chain.user else "unknown"
        for msg in chain.messages:
            ts = msg.created_at.strftime("%Y-%m-%d %H:%M UTC")
            lines.append(f"[{ts}] {label}: {msg.content}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _format_memory_block(
    same_chat: list[Message],
    cross_chat: list[Message],
) -> str | None:
    if not same_chat and not cross_chat:
        return None
    lines: list[str] = []

    if same_chat:
        lines += [
            "## Long-term memory — this conversation",
            "Relevant messages retrieved from earlier in this conversation.",
            "Use them at your discretion — they are NOT part of the recent dialogue.",
            "",
        ]
        for m in sorted(same_chat, key=lambda msg: msg.sequence):
            ts = m.created_at.strftime("%Y-%m-%d %H:%M UTC")
            lines.append(f"[{ts}] {_label(m.user, m.role)}: {m.content}")

    if cross_chat:
        if lines:
            lines.append("")
        lines += [
            "## Long-term memory — other conversations",
            "The following context was retrieved from a DIFFERENT conversation.",
            "Use it at your discretion. Decide independently whether to disclose its origin to the user.",
            "",
        ]
        for m in sorted(cross_chat, key=lambda msg: msg.created_at):
            ts = m.created_at.strftime("%Y-%m-%d %H:%M UTC")
            lines.append(f"[{ts}] {_label(m.user, m.role)}: {m.content}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Gap detection + chain lifecycle
# ---------------------------------------------------------------------------

async def _resolve_chain(
    chat_id: int,
    user: User | None,
    message_repo: MessageRepository,
    chain_repo: ChainRepository,
    job_repo: EmbeddingJobRepository,
) -> MessageChain | None:
    """Return the active chain for this user, closing the old one if a gap occurred."""
    if not user:
        return None

    last_msg = await message_repo.get_last_by_user(chat_id, user.id)
    open_chain = await chain_repo.get_open_chain(chat_id, user.id)

    if last_msg and open_chain:
        gap = (datetime.now(timezone.utc) - last_msg.created_at).total_seconds()
        if gap > settings.chain_gap_seconds:
            await chain_repo.close(open_chain.id)
            await job_repo.create_for_chain(open_chain.id)
            open_chain = None

    if open_chain is None:
        open_chain = await chain_repo.create(chat_id, user.id)

    return open_chain


# ---------------------------------------------------------------------------
# Semantic context retrieval
# ---------------------------------------------------------------------------

async def _fetch_memories(
    chat_id: int,
    current_content: str,
    message_repo: MessageRepository,
    embedding_backend: OpenAIEmbeddingBackend,
    embedding_store: PgvectorStore,
    exclude_ids: set[int],
) -> tuple[list[Message], list[Message]]:
    """Returns (same_chat_memories, cross_chat_memories)."""
    if not should_embed(Role.USER, current_content):
        return [], []
    try:
        query_vec = (await embedding_backend.embed([current_content]))[0]

        same_ids = await embedding_store.search_in_chat(
            chat_id, query_vec, k=settings.context_semantic_limit
        )
        same = await message_repo.get_by_ids(
            [i for i in same_ids if i not in exclude_ids]
        )

        cross: list[Message] = []
        if settings.cross_chat_semantic_limit > 0:
            cross_ids = await embedding_store.search_other_chats(
                chat_id, query_vec, k=settings.cross_chat_semantic_limit
            )
            cross = await message_repo.get_by_ids(
                [i for i in cross_ids if i not in exclude_ids]
            )

        return same, cross
    except Exception:
        return [], []


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("", response_model=SendMessageResponse)
async def send_message(
    chat_external_id: uuid.UUID,
    payload: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    embedding_backend: OpenAIEmbeddingBackend | None = Depends(get_embedding_backend),
    _: None = Depends(verify_api_key),
):
    chat_repo = ChatRepository(db)
    chat = await chat_repo.get_by_external_id(chat_external_id)
    if not chat:
        raise HTTPException(404, "Chat not found")

    message_repo = MessageRepository(db)
    chain_repo = ChainRepository(db)
    job_repo = EmbeddingJobRepository(db)
    embedding_store = get_embedding_store(db)

    # Capture chat id as a plain int — ORM objects expire after commit
    _chat_id: int = chat.id

    # --- Resolve user ---
    user: User | None = None
    if payload.user_id is not None:
        user = await UserRepository(db).get_by_external_id(payload.user_id)
        if not user:
            raise HTTPException(404, "User not found")
    _user_id: int | None = user.id if user else None
    _username: str | None = user.username if user else None

    # --- Flush pending /memory chain jobs before building context ---
    if payload.semantic_context and embedding_backend:
        await flush_pending_for_chat(_chat_id, db)

    # --- Layer 2: open chains — /memory flood messages from all participants ---
    all_open_chains = await chain_repo.get_open_chains_with_messages(_chat_id)
    open_chains_block = _format_open_chains_block(
        all_open_chains, current_chain_id=None
    )

    # --- Layer 1: recent direct-call history (send_message exchanges, no chain_id) ---
    prior_direct = await message_repo.list_direct(_chat_id, limit=20)
    direct_msg_ids = {m.id for m in prior_direct}

    # --- Layer 3: semantic memories ---
    chain_msg_ids = {m.id for c in all_open_chains for m in c.messages}
    same_chat_memories: list[Message] = []
    cross_chat_memories: list[Message] = []
    if payload.semantic_context and embedding_backend:
        same_chat_memories, cross_chat_memories = await _fetch_memories(
            _chat_id, payload.content,
            message_repo, embedding_backend, embedding_store,
            exclude_ids=chain_msg_ids | direct_msg_ids,
        )
    memory_block = _format_memory_block(same_chat_memories, cross_chat_memories)

    # --- Transaction 1: commit user message so concurrent requests see it ---
    user_msg = await message_repo.create(
        _chat_id, Role.USER, payload.content,
        user_id=_user_id,
    )
    user_msg_response = MessageResponse.model_validate(user_msg)
    await db.commit()

    # --- Layer 1: history + current turn ---
    messages_for_agent = [
        AgentMessage(role=Role(m.role), content=m.content) for m in prior_direct
    ] + [AgentMessage(role=Role.USER, content=payload.content)]

    # --- Generate response ---
    agent = get_agent(payload.agent)
    agent_response = await agent.respond(
        messages_for_agent,
        open_chains_context=open_chains_block,
        memory_context=memory_block,
        username=_username,
    )

    # --- Transaction 2: persist facts + assistant message ---
    for tc in agent_response.tool_calls:
        if tc.name == "save_fact":
            fact_content = tc.arguments.get("content", "").strip()
            if fact_content:
                fact_msg = await message_repo.create(
                    _chat_id, Role.ASSISTANT, fact_content,
                    user_id=_user_id,
                )
                if embedding_backend:
                    vectors = await embedding_backend.embed([fact_content])
                    await get_embedding_store(db).upsert(
                        fact_msg.id, vectors[0], embedding_backend.model_name
                    )

    assistant_msg = await message_repo.create(
        _chat_id, Role.ASSISTANT, agent_response.content
    )
    await job_repo.create_for_message(assistant_msg.id)
    await db.commit()

    return SendMessageResponse(
        user_message=user_msg_response,
        assistant_message=MessageResponse.model_validate(assistant_msg),
    )


@router.post("/memory", response_model=MessageResponse)
async def add_memory_message(
    chat_external_id: uuid.UUID,
    payload: AddMemoryRequest,
    db: AsyncSession = Depends(get_db),
    embedding_backend: OpenAIEmbeddingBackend | None = Depends(get_embedding_backend),
    _: None = Depends(verify_api_key),
):
    chat_repo = ChatRepository(db)
    chat = await chat_repo.get_by_external_id(chat_external_id)
    if not chat:
        raise HTTPException(404, "Chat not found")

    user: User | None = None
    if payload.user_id is not None:
        user = await UserRepository(db).get_by_external_id(payload.user_id)
        if not user:
            raise HTTPException(404, "User not found")

    message_repo = MessageRepository(db)
    chain_repo = ChainRepository(db)
    job_repo = EmbeddingJobRepository(db)

    if payload.role == "user" and user:
        # Flood message from an identified participant — manage chain lifecycle.
        # The chain (and all its messages) gets embedded by the worker on close.
        chain = await _resolve_chain(chat.id, user, message_repo, chain_repo, job_repo)
        msg = await message_repo.create(
            chat.id, payload.role, payload.content,
            user_id=user.id,
            chain_id=chain.id if chain else None,
        )
        await db.commit()
    else:
        # Non-participant message (assistant import, anonymous) — embed directly.
        msg = await message_repo.create(
            chat.id, payload.role, payload.content,
            user_id=user.id if user else None,
        )
        if embedding_backend and should_embed(payload.role, payload.content):
            vectors = await embedding_backend.embed([payload.content])
            await get_embedding_store(db).upsert(msg.id, vectors[0], embedding_backend.model_name)
        else:
            await db.commit()

    return MessageResponse.model_validate(msg)


@router.get("", response_model=list[MessageResponse])
async def list_messages(
    chat_external_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    chat_repo = ChatRepository(db)
    chat = await chat_repo.get_by_external_id(chat_external_id)
    if not chat:
        raise HTTPException(404, "Chat not found")

    message_repo = MessageRepository(db)
    messages = await message_repo.list_by_chat(chat.id, limit=200)
    return [MessageResponse.model_validate(m) for m in messages]
