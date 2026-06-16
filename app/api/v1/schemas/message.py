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
    semantic_context: bool = True
    cross_chat_context: bool = True
    metadata: dict[str, Any] | None = None


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
    tokens_remaining: int       # may be negative if last request exceeded the limit
    window_resets_at: datetime  # when tokens_used resets to 0


class SendMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
    token_usage: Optional[TokenBudgetUsage] = None


class MemoryFlushRequest(BaseModel):
    user_id: uuid.UUID | None = None


class MemoryFlushResponse(BaseModel):
    count: int
