import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.agent.schemas import AgentProvider


class SendMessageRequest(BaseModel):
    content: str
    participant_id: str | None = None
    agent: AgentProvider = AgentProvider.OPENAI
    semantic_context: bool = True


class AddMemoryRequest(BaseModel):
    content: str
    role: Literal["user", "assistant"] = "user"


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
