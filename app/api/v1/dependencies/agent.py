from app.agent.agent import Agent
from app.agent.backends.claude import ClaudeBackend
from app.agent.backends.deepseek import DeepSeekBackend
from app.agent.backends.openai import OpenAIBackend
from app.agent.exceptions import AgentConfigError
from app.agent.schemas import AgentProvider
from app.config.settings import settings

_registry: dict[AgentProvider, Agent] = {}


def _require_key(key: str, provider: AgentProvider) -> str:
    if not key:
        raise AgentConfigError(
            f"Provider '{provider}' is not configured: missing API key. "
            f"Set the corresponding environment variable and restart the service."
        )
    return key


_FACTORIES: dict[AgentProvider, object] = {
    AgentProvider.OPENAI: lambda: Agent(
        OpenAIBackend(api_key=_require_key(settings.openai_api_key, AgentProvider.OPENAI))
    ),
    AgentProvider.DEEPSEEK: lambda: Agent(
        DeepSeekBackend(api_key=_require_key(settings.deepseek_api_key, AgentProvider.DEEPSEEK))
    ),
    AgentProvider.CLAUDE: lambda: Agent(
        ClaudeBackend(api_key=_require_key(settings.anthropic_api_key, AgentProvider.CLAUDE))
    ),
}


def get_agent(provider: AgentProvider = AgentProvider.OPENAI) -> Agent:
    if provider not in _registry:
        factory = _FACTORIES[provider]
        _registry[provider] = factory()  # type: ignore[operator]
    return _registry[provider]
