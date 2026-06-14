from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class AgentProvider(StrEnum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    CLAUDE = "claude"


@dataclass(slots=True)
class AgentMessage:
    role: Role
    content: str


@dataclass(slots=True)
class AgentResponse:
    content: str
    model: str

    raw: Any = field(default=None, repr=False)
