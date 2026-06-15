import asyncio
import logging

from app.agent.embedding.base import should_embed
from app.agent.embedding.stores.pgvector import PgvectorStore
from app.config.settings import settings
from app.db.models.embedding_job import EmbeddingJob
from app.db.models.message import MessageType
from app.db.session import AsyncSessionLocal
from app.repositories.chain import ChainRepository
from app.repositories.embedding_job import EmbeddingJobRepository
from app.repositories.message import MessageRepository

logger = logging.getLogger(__name__)

_backend = None
_backend_initialized = False


def _get_backend():
    """Return the worker-local embedding backend (singleton, loaded once)."""
    global _backend, _backend_initialized
    if _backend_initialized:
        return _backend
    _backend_initialized = True
    from app.config.settings import settings
    name = settings.embedding_backend.lower()
    if name == "sentence_transformers":
        from app.agent.embedding.backends.sentence_transformers import SentenceTransformersBackend
        _backend = SentenceTransformersBackend(settings.st_model)
    elif name == "openai":
        if settings.openai_api_key:
            from app.agent.embedding.backends.openai import OpenAIEmbeddingBackend
            _backend = OpenAIEmbeddingBackend()
    if _backend is None:
        logger.warning("No embedding backend configured — worker will skip jobs")
    return _backend


async def process_jobs(jobs: list[EmbeddingJob], session, backend=None) -> None:
    """Process a list of already-claimed embedding jobs using the given session.

    Pass ``backend`` explicitly when calling from a context that has its own
    embedding backend (e.g. the API flushing jobs via RemoteEmbeddingBackend).
    When omitted, falls back to the worker-local backend.
    """
    if not jobs:
        return

    if backend is None:
        backend = _get_backend()
    if backend is None:
        return
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
                await store.upsert(target_id, vectors[0], backend.model_name)

                # Safety cap: trim oldest facts when a user exceeds the limit.
                if (
                    job.message_id is not None
                    and msg is not None
                    and msg.message_type == MessageType.FACT
                    and msg.user_id is not None
                ):
                    deleted = await message_repo.trim_old_facts(
                        msg.chat_id, msg.user_id, settings.facts_per_user_limit
                    )
                    if deleted:
                        logger.info(
                            "Trimmed %d old fact(s) for user_id=%d in chat_id=%d",
                            deleted, msg.user_id, msg.chat_id,
                        )

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


async def flush_pending_for_chat(chat_id: int, backend=None) -> None:
    """Process all pending jobs for a chat before context building.

    Pass ``backend`` when calling from the API so jobs are embedded via
    RemoteEmbeddingBackend instead of the worker-local backend.
    """
    async with AsyncSessionLocal() as session:
        job_repo = EmbeddingJobRepository(session)
        jobs = await job_repo.claim_pending_for_chat(chat_id, limit=50)
        await process_jobs(jobs, session, backend=backend)


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
        logger.debug("Auto-closed abandoned chain %d (user_id=%s)", chain.id, chain.user_id)

    await session.commit()
    logger.info("Closed %d abandoned chain(s)", len(abandoned))


async def _worker_loop() -> None:
    logger.info("Embedding worker started (poll interval: %ss)", settings.embedding_worker_poll_interval)
    async with AsyncSessionLocal() as session:
        job_repo = EmbeddingJobRepository(session)
        recovered = await job_repo.recover_stale()
        await session.commit()
        if recovered:
            logger.info("Recovered %d stale processing job(s)", recovered)
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
