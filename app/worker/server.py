import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.config.settings import settings
from app.worker.embedding import _get_backend, start_worker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    backend = _get_backend()
    if backend:
        logger.info("Preloading embedding model...")
        await backend.embed(["warmup"])
        logger.info("Embedding model ready")
    else:
        logger.warning("No embedding backend available — /embed will return 503")
    task = start_worker()
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


class EmbedRequest(BaseModel):
    texts: list[str] = Field(max_length=32)

    @field_validator("texts")
    @classmethod
    def validate_text_lengths(cls, v: list[str]) -> list[str]:
        for text in v:
            if len(text) > 32_000:
                raise ValueError("each text must be at most 32 000 characters")
        return v


class EmbedResponse(BaseModel):
    vectors: list[list[float]]
    model: str


async def _verify_worker_key(x_worker_key: str = Header(...)) -> None:
    expected = settings.effective_worker_api_key
    if not hmac.compare_digest(x_worker_key.encode(), expected.encode()):
        raise HTTPException(401, "Unauthorized")


@app.get("/health")
async def health() -> dict:
    """Unauthenticated — used by Docker healthcheck from within the container."""
    backend = _get_backend()
    if backend is None:
        raise HTTPException(503, "Embedding backend not configured")
    return {"status": "ok", "model": backend.model_name}


@app.post("/embed", response_model=EmbedResponse, dependencies=[Depends(_verify_worker_key)])
async def embed(request: EmbedRequest) -> EmbedResponse:
    backend = _get_backend()
    if backend is None:
        raise HTTPException(503, "Embedding backend not configured")
    vectors = await backend.embed(request.texts)
    return EmbedResponse(vectors=vectors, model=backend.model_name)
