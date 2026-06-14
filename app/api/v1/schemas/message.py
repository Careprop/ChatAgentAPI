import uuid
from datetime import datetime

from pydantic import BaseModel

from app.agent.schemas import AgentProvider


class SendMessageRequest(BaseModel):
    content: str
    agent: AgentProvider = AgentProvider.OPENAI


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
