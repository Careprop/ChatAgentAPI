from app.agent.agent import Agent, DEFAULT_INSTRUCTIONS
from app.agent.backends import OpenAIBackend
from app.agent.base import AgentBackend
from app.agent.schemas import AgentMessage, AgentResponse, Role

__all__ = [
    "Agent",
    "AgentBackend",
    "AgentMessage",
    "AgentResponse",
    "DEFAULT_INSTRUCTIONS",
    "OpenAIBackend",
    "Role",
    "get_agent",
]


def get_agent() -> Agent:
    """Build the default agent backed by OpenAI."""
    return Agent(OpenAIBackend())
