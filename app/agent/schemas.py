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
class ToolDefinition:
    name: str
    description: str
    parameters: dict  # JSON Schema object


@dataclass(slots=True)
class ToolCall:
    name: str
    arguments: dict


@dataclass(slots=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(slots=True)
class AgentResponse:
    content: str
    model: str

    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: TokenUsage | None = None
    raw: Any = field(default=None, repr=False)
