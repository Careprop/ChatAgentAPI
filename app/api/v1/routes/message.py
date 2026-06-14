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
from app.repositories.chain import ChainRepository
from app.repositories.chat import ChatRepository
from app.repositories.embedding_job import EmbeddingJobRepository
from app.repositories.message import MessageRepository
from app.worker.embedding import flush_pending_for_chat

router = APIRouter(
    prefix="/api/v1/chat/{chat_external_id}/messages",
    tags=["messages"],
)


# ---------------------------------------------------------------------------
# Context formatting helpers
# ---------------------------------------------------------------------------

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
        label = chain.participant_id or "unknown"
        for msg in chain.messages:
            ts = msg.created_at.strftime("%Y-%m-%d %H:%M UTC")
            lines.append(f"[{ts}] {label}: {msg.content}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _format_memory_block(memories: list[Message]) -> str | None:
    if not memories:
        return None
    lines = [
        "## Long-term memory (retrieved by semantic search)",
        "Relevant messages from earlier in this conversation.",
        "Use them at your discretion — they are NOT part of the recent dialogue.",
        "",
    ]
    for m in sorted(memories, key=lambda msg: msg.sequence):
        ts = m.created_at.strftime("%Y-%m-%d %H:%M UTC")
        participant = m.participant_id or m.role
        lines.append(f"[{ts}] {participant}: {m.content}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Gap detection + chain lifecycle
# ---------------------------------------------------------------------------

async def _resolve_chain(
    chat_id: int,
    participant_id: str | None,
    message_repo: MessageRepository,
    chain_repo: ChainRepository,
    job_repo: EmbeddingJobRepository,
) -> MessageChain | None:
    """Return the active chain for this participant, closing the old one if a gap occurred."""
    if not participant_id:
        return None

    last_msg = await message_repo.get_last_by_participant(chat_id, participant_id)
    open_chain = await chain_repo.get_open_chain(chat_id, participant_id)

    if last_msg and open_chain:
        gap = (datetime.now(timezone.utc) - last_msg.created_at).total_seconds()
        if gap > settings.chain_gap_seconds:
            await chain_repo.close(open_chain.id)
            await job_repo.create_for_chain(open_chain.id)
            open_chain = None

    if open_chain is None:
        open_chain = await chain_repo.create(chat_id, participant_id)

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
) -> list[Message]:
    if not should_embed(Role.USER, current_content):
        return []
    try:
        query_vec = (await embedding_backend.embed([current_content]))[0]
        semantic_ids = await embedding_store.search_in_chat(
            chat_id, query_vec, k=settings.context_semantic_limit
        )
        novel_ids = [i for i in semantic_ids if i not in exclude_ids]
        return await message_repo.get_by_ids(novel_ids) if novel_ids else []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("", response_model=SendMessageResponse)
async def send_message(
    chat_external_id: uuid.UUID,
    payload: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    embedding_backend: OpenAIEmbeddingBackend = Depends(get_embedding_backend),
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

    # --- Chain lifecycle (gap detection) ---
    chain = await _resolve_chain(
        chat.id, payload.participant_id, message_repo, chain_repo, job_repo
    )

    # --- Flush pending embedding jobs for this chat before building context ---
    if payload.semantic_context:
        await flush_pending_for_chat(chat.id, db)

    # --- Layer 2: open chains from OTHER participants ---
    all_open_chains = await chain_repo.get_open_chains_with_messages(chat.id)
    open_chains_block = _format_open_chains_block(
        all_open_chains, current_chain_id=chain.id if chain else None
    )

    # --- Current chain fragments (messages array prefix) ---
    chain_messages: list[AgentMessage] = []
    if chain:
        prior = await message_repo.list_by_chain(chain.id)
        chain_messages = [AgentMessage(role=Role(m.role), content=m.content) for m in prior]

    # --- Layer 3: semantic memories ---
    chain_msg_ids = {m.id for c in all_open_chains for m in c.messages}
    memories: list[Message] = []
    if payload.semantic_context:
        memories = await _fetch_memories(
            chat.id, payload.content,
            message_repo, embedding_backend, embedding_store,
            exclude_ids=chain_msg_ids,
        )
    memory_block = _format_memory_block(memories)

    # --- Persist user message ---
    user_msg = await message_repo.create(
        chat.id, Role.USER, payload.content,
        participant_id=payload.participant_id,
        chain_id=chain.id if chain else None,
    )

    # --- Layer 1: messages array = chain context + current message ---
    messages_for_agent = chain_messages + [AgentMessage(role=Role.USER, content=payload.content)]

    # --- Generate response ---
    agent = get_agent(payload.agent)
    agent_response = await agent.respond(
        messages_for_agent,
        open_chains_context=open_chains_block,
        memory_context=memory_block,
    )

    # --- Persist assistant message + queue its embedding job ---
    assistant_msg = await message_repo.create(
        chat.id, Role.ASSISTANT, agent_response.content
    )
    await job_repo.create_for_message(assistant_msg.id)

    await db.commit()

    return SendMessageResponse(
        user_message=MessageResponse.model_validate(user_msg),
        assistant_message=MessageResponse.model_validate(assistant_msg),
    )


@router.post("/memory", response_model=MessageResponse)
async def add_memory_message(
    chat_external_id: uuid.UUID,
    payload: AddMemoryRequest,
    db: AsyncSession = Depends(get_db),
    embedding_backend: OpenAIEmbeddingBackend = Depends(get_embedding_backend),
    _: None = Depends(verify_api_key),
):
    chat_repo = ChatRepository(db)
    chat = await chat_repo.get_by_external_id(chat_external_id)
    if not chat:
        raise HTTPException(404, "Chat not found")

    message_repo = MessageRepository(db)
    msg = await message_repo.create(chat.id, payload.role, payload.content)

    if should_embed(payload.role, payload.content):
        vectors = await embedding_backend.embed([payload.content])
        store = get_embedding_store(db)
        await store.upsert(msg.id, vectors[0], embedding_backend._model)
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
