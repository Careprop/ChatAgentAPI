from fastapi import APIRouter, Depends

from app.agent.schemas import AgentProvider
from app.api.v1.dependencies.auth import verify_api_key
from app.api.v1.schemas.agent import AgentInfo
from app.config.settings import settings

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.get("", response_model=list[AgentInfo])
async def list_agents(_: None = Depends(verify_api_key)):
    provider_config = [
        (AgentProvider.OPENAI,   settings.openai_api_key,    settings.openai_model),
        (AgentProvider.DEEPSEEK, settings.deepseek_api_key,  settings.deepseek_model),
        (AgentProvider.CLAUDE,   settings.anthropic_api_key, settings.anthropic_model),
    ]
    return [
        AgentInfo(provider=provider, model=model)
        for provider, api_key, model in provider_config
        if api_key
    ]
