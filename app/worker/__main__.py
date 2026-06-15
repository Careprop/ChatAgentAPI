import asyncio
import logging

# Import all ORM models so SQLAlchemy can resolve relationships before any query runs.
import app.db.models.chain  # noqa: F401
import app.db.models.chat  # noqa: F401
import app.db.models.embedding_job  # noqa: F401
import app.db.models.message  # noqa: F401
import app.db.models.message_embedding  # noqa: F401
import app.db.models.user  # noqa: F401

from app.worker.embedding import _worker_loop

logging.basicConfig(level=logging.INFO)

asyncio.run(_worker_loop())
