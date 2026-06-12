import uuid

from datetime import datetime

from pydantic import BaseModel


class ChatCreate(BaseModel):
    title: str


class ChatResponse(BaseModel):
    external_id: uuid.UUID
    title: str

    created_at: datetime

    model_config = {
        "from_attributes": True
    }
