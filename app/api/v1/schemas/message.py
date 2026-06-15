import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.agent.schemas import AgentProvider


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=32_000)
    user_id: uuid.UUID | None = None
    agent: AgentProvider = AgentProvider.OPENAI
    semantic_context: bool = True


class AddMemoryRequest(BaseModel):
    content: str = Field(min_length=1, max_length=32_000)
    role: Literal["user", "assistant"] = "user"
    user_id: uuid.UUID | None = None


class MessageResponse(BaseModel):
    external_id: uuid.UUID
    role: str
    content: str
    sequence: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SendMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
