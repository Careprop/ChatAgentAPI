import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ChatCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    external_key: str | None = Field(None, max_length=255)


class ChatResponse(BaseModel):
    external_id: uuid.UUID
    title: str
    external_key: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
