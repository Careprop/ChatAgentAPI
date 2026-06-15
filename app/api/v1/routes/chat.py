import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import verify_api_key
from app.api.v1.dependencies.db import get_db
from app.api.v1.dependencies.rate_limit import limiter
from app.api.v1.schemas.chat import (
    ChatCreate,
    ChatResponse
)
from app.repositories.chat import ChatRepository

router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat"]
)


@router.post(
    path="",
    response_model=ChatResponse
)
@limiter.limit("60/minute")
async def create_chat(
    request: Request,
    payload: ChatCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    repo = ChatRepository(db)
    chat = await repo.create(payload.title)
    await db.commit()
    return chat


@router.get("", response_model=list[ChatResponse])
async def list_chats(
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    repo = ChatRepository(db)
    chats = await repo.list_active(limit=limit)
    return [ChatResponse.model_validate(c) for c in chats]


@router.get(
    path="/{external_id}",
    response_model=ChatResponse
)
async def get_chat(
    external_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    repo = ChatRepository(db)

    chat = await repo.get_by_external_id(external_id)

    if not chat:
        raise HTTPException(404, "Chat not found")

    return chat


@router.delete("/{external_id}", status_code=204)
async def delete_chat(
    external_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    repo = ChatRepository(db)
    chat = await repo.get_by_external_id(external_id)
    if not chat:
        raise HTTPException(404, "Chat not found")
    await repo.delete(chat)
    await db.commit()
    return Response(status_code=204)
