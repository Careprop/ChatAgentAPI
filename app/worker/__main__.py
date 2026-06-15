import logging

import uvicorn

# Import all ORM models so SQLAlchemy can resolve relationships before any query runs.
import app.db.models.chain  # noqa: F401
import app.db.models.chat  # noqa: F401
import app.db.models.embedding_job  # noqa: F401
import app.db.models.message  # noqa: F401
import app.db.models.message_embedding  # noqa: F401
import app.db.models.user  # noqa: F401

logging.basicConfig(level=logging.INFO)

uvicorn.run("app.worker.server:app", host="0.0.0.0", port=8001, log_level="info")
