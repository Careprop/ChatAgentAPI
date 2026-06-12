from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import verify_api_key
from app.api.v1.dependencies.db import get_db
from app.api.v1.schemas.chat import (
    ChatCreate,
    ChatResponse
)
from app.db.models.chat import Chat

router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat"]
)


@router.post(
    "",
    response_model=ChatResponse
)
async def create_chat(
    payload: ChatCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    chat = Chat(
        title=payload.title
    )

    db.add(chat)
    await db.commit()
    await db.refresh(chat)

    return chat


@router.get(
    "",
    response_model=ChatResponse
)
async def get_chat(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    chat = await db.get(Chat, chat_id)

    return chat
