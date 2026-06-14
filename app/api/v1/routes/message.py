import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.embedding.backends.openai import OpenAIEmbeddingBackend
from app.agent.embedding.base import should_embed
from app.agent.embedding.stores.pgvector import PgvectorStore
from app.agent.schemas import AgentMessage, Role
from app.api.v1.dependencies.agent import get_agent
from app.api.v1.dependencies.auth import verify_api_key
from app.api.v1.dependencies.db import get_db
from app.api.v1.dependencies.embedding import get_embedding_backend, get_embedding_store
from app.api.v1.schemas.message import MessageResponse, SendMessageRequest, SendMessageResponse
from app.config.settings import settings
from app.db.models.message import Message
from app.db.session import AsyncSessionLocal
from app.repositories.chat import ChatRepository
from app.repositories.message import MessageRepository

router = APIRouter(
    prefix="/api/v1/chat/{chat_external_id}/messages",
    tags=["messages"],
)


async def _embed_messages(
    messages: list[tuple[int, str, str]],
    backend: OpenAIEmbeddingBackend,
) -> None:
    """Background task: generate and persist embeddings for a batch of messages."""
    to_embed = [
        (mid, role, content)
        for mid, role, content in messages
        if should_embed(role, content)
    ]
    if not to_embed:
        return

    texts = [content for _, _, content in to_embed]
    vectors = await backend.embed(texts)

    async with AsyncSessionLocal() as session:
        store = PgvectorStore(session)
        for (message_id, _, _), vector in zip(to_embed, vectors):
            await store.upsert(message_id, vector, backend._model)


async def _build_context(
    chat_id: int,
    current_content: str,
    message_repo: MessageRepository,
    embedding_backend: OpenAIEmbeddingBackend,
    embedding_store: PgvectorStore,
) -> list[AgentMessage]:
    """Hybrid context: recent messages + semantically relevant older messages."""
    recent: list[Message] = await message_repo.list_by_chat(
        chat_id, limit=settings.context_recency_limit
    )
    seen_ids = {m.id for m in recent}
    extra: list[Message] = []

    if should_embed(Role.USER, current_content):
        try:
            query_vec = (await embedding_backend.embed([current_content]))[0]
            semantic_ids = await embedding_store.search_in_chat(
                chat_id, query_vec, k=settings.context_semantic_limit
            )
            novel_ids = [i for i in semantic_ids if i not in seen_ids]
            if novel_ids:
                extra = await message_repo.get_by_ids(novel_ids)
        except Exception:
            # Semantic retrieval is best-effort; fall back to recency-only.
            pass

    all_messages = sorted(extra + recent, key=lambda m: m.sequence)

    seen: set[int] = set()
    deduped: list[Message] = []
    for m in all_messages:
        if m.id not in seen:
            seen.add(m.id)
            deduped.append(m)

    return [AgentMessage(role=Role(m.role), content=m.content) for m in deduped]


@router.post("", response_model=SendMessageResponse)
async def send_message(
    chat_external_id: uuid.UUID,
    payload: SendMessageRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    embedding_backend: OpenAIEmbeddingBackend = Depends(get_embedding_backend),
    _: None = Depends(verify_api_key),
):
    chat_repo = ChatRepository(db)
    chat = await chat_repo.get_by_external_id(chat_external_id)
    if not chat:
        raise HTTPException(404, "Chat not found")

    message_repo = MessageRepository(db)
    embedding_store = get_embedding_store(db)

    context = await _build_context(
        chat.id, payload.content, message_repo, embedding_backend, embedding_store
    )

    user_msg = await message_repo.create(chat.id, Role.USER, payload.content)
    context.append(AgentMessage(role=Role.USER, content=payload.content))

    agent = get_agent(payload.agent)
    agent_response = await agent.respond(context)
    assistant_msg = await message_repo.create(chat.id, Role.ASSISTANT, agent_response.content)

    await db.commit()

    background_tasks.add_task(
        _embed_messages,
        [
            (user_msg.id, user_msg.role, user_msg.content),
            (assistant_msg.id, assistant_msg.role, assistant_msg.content),
        ],
        embedding_backend,
    )

    return SendMessageResponse(
        user_message=MessageResponse.model_validate(user_msg),
        assistant_message=MessageResponse.model_validate(assistant_msg),
    )


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
