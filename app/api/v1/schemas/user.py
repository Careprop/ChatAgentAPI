import uuid
from datetime import datetime

from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str


class UserResponse(BaseModel):
    external_id: uuid.UUID
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}
