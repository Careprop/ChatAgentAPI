from pydantic import BaseModel


class ChatCreate(BaseModel):
    title: str


class ChatResponse(BaseModel):
    id: int
    title: str

    model_config = {
        "from_attributes": True
    }
