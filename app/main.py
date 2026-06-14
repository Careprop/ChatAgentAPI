import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.agent.exceptions import (
    AgentAuthError,
    AgentConfigError,
    AgentError,
    AgentProviderError,
    AgentRateLimitError,
    AgentTimeoutError,
)
from app.api.v1.routes.chat import router as chat_router
from app.api.v1.routes.message import router as message_router
from app.worker.embedding import start_worker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_task = start_worker()
    yield
    worker_task.cancel()


app = FastAPI(lifespan=lifespan)

app.include_router(chat_router)
app.include_router(message_router)


@app.exception_handler(AgentConfigError)
async def _handle_agent_config_error(request: Request, exc: AgentConfigError) -> JSONResponse:
    logger.error("Agent configuration error: %s", exc)
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(AgentAuthError)
async def _handle_agent_auth_error(request: Request, exc: AgentAuthError) -> JSONResponse:
    logger.error("Agent authentication error: %s", exc)
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(AgentRateLimitError)
async def _handle_agent_rate_limit(request: Request, exc: AgentRateLimitError) -> JSONResponse:
    logger.warning("Agent rate limit: %s", exc)
    return JSONResponse(status_code=429, content={"detail": str(exc)})


@app.exception_handler(AgentTimeoutError)
async def _handle_agent_timeout(request: Request, exc: AgentTimeoutError) -> JSONResponse:
    logger.warning("Agent timeout: %s", exc)
    return JSONResponse(status_code=504, content={"detail": str(exc)})


@app.exception_handler(AgentProviderError)
async def _handle_agent_provider_error(request: Request, exc: AgentProviderError) -> JSONResponse:
    logger.error("Agent provider error: %s", exc)
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(AgentError)
async def _handle_agent_error(request: Request, exc: AgentError) -> JSONResponse:
    logger.error("Unexpected agent error: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal agent error"})
