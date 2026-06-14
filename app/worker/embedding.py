import asyncio
import logging

from app.agent.embedding.backends.openai import OpenAIEmbeddingBackend
from app.agent.embedding.base import should_embed
from app.agent.embedding.stores.pgvector import PgvectorStore
from app.config.settings import settings
from app.db.models.embedding_job import EmbeddingJob
from app.db.session import AsyncSessionLocal
from app.repositories.chain import ChainRepository
from app.repositories.embedding_job import EmbeddingJobRepository
from app.repositories.message import MessageRepository

logger = logging.getLogger(__name__)

_embedding_backend: OpenAIEmbeddingBackend | None = None


def _get_backend() -> OpenAIEmbeddingBackend:
    global _embedding_backend
    if _embedding_backend is None:
        _embedding_backend = OpenAIEmbeddingBackend()
    return _embedding_backend


async def process_jobs(jobs: list[EmbeddingJob], session) -> None:
    """Process a list of already-claimed embedding jobs using the given session."""
    if not jobs:
        return

    backend = _get_backend()
    job_repo = EmbeddingJobRepository(session)
    message_repo = MessageRepository(session)
    chain_repo = ChainRepository(session)
    store = PgvectorStore(session)

    for job in jobs:
        try:
            if job.chain_id is not None:
                messages = await message_repo.list_by_chain(job.chain_id)
                if not messages:
                    await job_repo.mark_done(job.id)
                    continue
                text = "\n".join(f"{m.role}: {m.content}" for m in messages)
                target_id = messages[-1].id
            else:
                msg = await message_repo.get_by_id(job.message_id)
                if msg is None:
                    await job_repo.mark_done(job.id)
                    continue
                text = msg.content
                target_id = msg.id

            if should_embed("user", text):
                vectors = await backend.embed([text])
                await store.upsert(target_id, vectors[0], backend._model)

            if job.chain_id is not None:
                await chain_repo.mark_embedded(job.chain_id)

            await job_repo.mark_done(job.id)
            await session.commit()

        except Exception as exc:
            logger.error("Embedding job %d failed: %s", job.id, exc)
            try:
                await session.rollback()
                async with AsyncSessionLocal() as err_session:
                    err_repo = EmbeddingJobRepository(err_session)
                    await err_repo.mark_failed(
                        job.id, str(exc), settings.embedding_job_max_attempts
                    )
                    await err_session.commit()
            except Exception:
                logger.exception("Failed to record job failure for job %d", job.id)


async def flush_pending_for_chat(chat_id: int, session) -> None:
    """Synchronously process all pending jobs for a chat before context building."""
    job_repo = EmbeddingJobRepository(session)
    jobs = await job_repo.claim_pending_for_chat(chat_id, limit=50)
    await process_jobs(jobs, session)


async def _close_abandoned_chains(session) -> None:
    """Find open chains with no recent activity and close them."""
    chain_repo = ChainRepository(session)
    job_repo = EmbeddingJobRepository(session)

    abandoned = await chain_repo.get_abandoned_chains(settings.chain_gap_seconds)
    if not abandoned:
        return

    for chain in abandoned:
        await chain_repo.close(chain.id)
        await job_repo.create_for_chain(chain.id)
        logger.debug("Auto-closed abandoned chain %d (participant=%s)", chain.id, chain.participant_id)

    await session.commit()
    logger.info("Closed %d abandoned chain(s)", len(abandoned))


async def _worker_loop() -> None:
    logger.info("Embedding worker started (poll interval: %ss)", settings.embedding_worker_poll_interval)
    while True:
        try:
            async with AsyncSessionLocal() as session:
                await _close_abandoned_chains(session)
                job_repo = EmbeddingJobRepository(session)
                jobs = await job_repo.claim_pending(limit=10)
                await session.commit()
                if jobs:
                    await process_jobs(jobs, session)
        except Exception:
            logger.exception("Embedding worker error")
        await asyncio.sleep(settings.embedding_worker_poll_interval)


def start_worker() -> asyncio.Task:
    return asyncio.create_task(_worker_loop(), name="embedding-worker")
