import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import verify_api_key
from app.api.v1.dependencies.db import get_db
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
async def create_chat(
    payload: ChatCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    repo = ChatRepository(db)

    return await repo.create(payload.title)


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
