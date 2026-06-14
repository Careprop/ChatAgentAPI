from pydantic import BaseModel

from app.agent.schemas import AgentProvider


class AgentInfo(BaseModel):
    provider: AgentProvider
    model: str
