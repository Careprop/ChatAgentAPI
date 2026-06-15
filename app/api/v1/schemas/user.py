import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")


class UserResponse(BaseModel):
    external_id: uuid.UUID
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}
