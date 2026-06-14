from app.agent.embedding.base import EmbeddingBackend


def create_embedding_backend() -> EmbeddingBackend | None:
    """Return the configured embedding backend, or None if not available."""
    from app.config.settings import settings

    backend = settings.embedding_backend.lower()

    if backend == "openai":
        if not settings.openai_api_key:
            return None
        from app.agent.embedding.backends.openai import OpenAIEmbeddingBackend
        return OpenAIEmbeddingBackend()

    if backend == "sentence_transformers":
        from app.agent.embedding.backends.sentence_transformers import SentenceTransformersBackend
        return SentenceTransformersBackend(settings.st_model)

    return None
