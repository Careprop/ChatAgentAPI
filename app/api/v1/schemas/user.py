import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    client_id: str = Field(min_length=1, max_length=128)
    display_name: str | None = Field(None, max_length=256)


class UserResponse(BaseModel):
    external_id: uuid.UUID
    client_id: str
    display_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
