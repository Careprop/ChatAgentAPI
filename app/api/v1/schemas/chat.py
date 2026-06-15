import uuid

from datetime import datetime

from pydantic import BaseModel, Field


class ChatCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)


class ChatResponse(BaseModel):
    external_id: uuid.UUID
    title: str

    created_at: datetime

    model_config = {
        "from_attributes": True
    }
