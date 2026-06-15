from app.agent.embedding.base import EmbeddingBackend

_backend: EmbeddingBackend | None = None
_init_attempted = False


def get_embedding_backend() -> EmbeddingBackend | None:
    """Return the configured embedding backend (process-wide singleton)."""
    global _backend, _init_attempted
    if not _init_attempted:
        _init_attempted = True
        _backend = _create()
    return _backend


def _create() -> EmbeddingBackend | None:
    from app.config.settings import settings

    backend = settings.embedding_backend.lower()

    if backend == "openai":
        if not settings.openai_api_key:
            return None
        from app.agent.embedding.backends.openai import OpenAIEmbeddingBackend
        return OpenAIEmbeddingBackend()

    if backend == "sentence_transformers":
        from app.agent.embedding.backends.remote import RemoteEmbeddingBackend
        return RemoteEmbeddingBackend(
            settings.worker_embed_url,
            settings.st_model,
            api_key=settings.effective_worker_api_key,
        )

    return None
