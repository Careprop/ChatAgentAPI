from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.embedding_job import EmbeddingJob, JobStatus
from app.db.models.message import Message
from app.db.models.message_embedding import MessageEmbedding


class EmbeddingJobRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_for_chain(self, chain_id: int) -> EmbeddingJob:
        job = EmbeddingJob(chain_id=chain_id, status=JobStatus.PENDING)
        self._session.add(job)
        await self._session.flush()
        return job

    async def create_for_message(self, message_id: int) -> EmbeddingJob:
        job = EmbeddingJob(message_id=message_id, status=JobStatus.PENDING)
        self._session.add(job)
        await self._session.flush()
        return job

    async def claim_pending(self, *, limit: int = 10) -> list[EmbeddingJob]:
        """Atomically claim pending jobs — safe for concurrent workers."""
        result = await self._session.execute(
            select(EmbeddingJob)
            .where(EmbeddingJob.status == JobStatus.PENDING)
            .order_by(EmbeddingJob.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        jobs = list(result.scalars().all())
        if jobs:
            ids = [j.id for j in jobs]
            await self._session.execute(
                update(EmbeddingJob)
                .where(EmbeddingJob.id.in_(ids))
                .values(status=JobStatus.PROCESSING)
            )
        return jobs

    async def claim_pending_for_chat(
        self, chat_id: int, *, limit: int = 50
    ) -> list[EmbeddingJob]:
        """Claim pending jobs scoped to a specific chat (used for flush at generation)."""
        result = await self._session.execute(
            select(EmbeddingJob)
            .outerjoin(Message, Message.id == EmbeddingJob.message_id)
            .where(
                EmbeddingJob.status == JobStatus.PENDING,
                (EmbeddingJob.message_id.is_(None)) | (Message.chat_id == chat_id),
            )
            .order_by(EmbeddingJob.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        jobs = list(result.scalars().all())
        if jobs:
            ids = [j.id for j in jobs]
            await self._session.execute(
                update(EmbeddingJob)
                .where(EmbeddingJob.id.in_(ids))
                .values(status=JobStatus.PROCESSING)
            )
        return jobs

    async def mark_done(self, job_id: int) -> None:
        await self._session.execute(
            update(EmbeddingJob)
            .where(EmbeddingJob.id == job_id)
            .values(
                status=JobStatus.DONE,
                processed_at=datetime.now(timezone.utc),
            )
        )

    async def mark_failed(self, job_id: int, error: str, max_attempts: int) -> None:
        result = await self._session.execute(
            select(EmbeddingJob).where(EmbeddingJob.id == job_id)
        )
        job = result.scalar_one()
        new_attempts = job.attempts + 1
        new_status = JobStatus.FAILED if new_attempts >= max_attempts else JobStatus.PENDING
        await self._session.execute(
            update(EmbeddingJob)
            .where(EmbeddingJob.id == job_id)
            .values(
                status=new_status,
                attempts=new_attempts,
                last_error=error,
            )
        )
