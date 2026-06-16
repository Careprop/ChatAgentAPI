import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.agent.schemas import AgentProvider


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=32_000)
    user_id: uuid.UUID | None = None
    display_name: str | None = Field(None, max_length=256)
    agent: AgentProvider = AgentProvider.OPENAI
    metadata: dict[str, Any] | None = None
    debug: bool = False


class AddMemoryRequest(BaseModel):
    content: str = Field(min_length=1, max_length=32_000)
    role: Literal["user", "assistant"] = "user"
    user_id: uuid.UUID | None = None
    display_name: str | None = Field(None, max_length=256)
    metadata: dict[str, Any] | None = None


class MessageResponse(BaseModel):
    external_id: uuid.UUID
    role: str
    content: str
    sequence: int
    created_at: datetime
    metadata: dict[str, Any] | None = Field(None, validation_alias="msg_metadata")

    model_config = {"from_attributes": True, "populate_by_name": True}


class TokenBudgetUsage(BaseModel):
    tokens_used: int
    token_budget: int
    tokens_remaining: int
    window_resets_at: datetime


class DebugMessage(BaseModel):
    role: str
    content: str
    sequence: int


class DebugContext(BaseModel):
    layer1_history: list[DebugMessage]
    layer3_user_facts: list[DebugMessage]
    layer3_chat_facts: list[DebugMessage]


class SendMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
    token_usage: Optional[TokenBudgetUsage] = None
    debug_context: Optional[DebugContext] = None
