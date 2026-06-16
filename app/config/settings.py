from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-5.4-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # Embedding backend: "sentence_transformers" | "openai"
    embedding_backend: str = "sentence_transformers"
    # sentence-transformers model name (used when embedding_backend = "sentence_transformers")
    st_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    # Must match the chosen model's output size; migration required when changing
    embedding_dimensions: int = 384
    # Internal URL of the worker embedding service (used when embedding_backend = "sentence_transformers")
    worker_embed_url: str = "http://worker:8001"

    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # How many semantically relevant messages added to context (same chat)
    context_semantic_limit: int = 4
    # How many cross-chat memories to include (0 = disabled)
    cross_chat_semantic_limit: int = 2
    # How many recent direct send_message exchanges to include in Layer 1
    context_direct_limit: int = 20
    # How many deduplicated facts to include in context per user
    context_facts_limit: int = 3
    # Cosine distance threshold: facts closer than this are considered duplicates
    fact_dedup_threshold: float = 0.15
    # Hard cap on stored facts per user per chat (oldest deleted when exceeded)
    facts_per_user_limit: int = 20

    # Seconds of silence after which a participant's chain is auto-closed
    chain_gap_seconds: int = 5
    # Open chains with no activity for longer than this are excluded from Layer 2 context
    max_chain_age_seconds: int = 300
    # Max simultaneous in-flight send_message requests per chat
    max_chat_concurrent: int = 5
    # Per-user token budget: max tokens per rolling window (future: override per user)
    token_budget: int = 10_000
    # Rolling window duration for per-user token budget (hours)
    token_window_hours: int = 4

    # Embedding worker (used by worker service only)
    embedding_worker_poll_interval: float = 2.0
    embedding_job_max_attempts: int = 3
    # Shared secret for API→worker internal calls; falls back to api_key if empty
    worker_api_key: str = ""

    # Per-provider output token limits
    openai_max_tokens: int = 8192
    deepseek_max_tokens: int = 8192
    anthropic_max_tokens: int = 8192

    api_key: str

    postgres_host: str
    postgres_port: int

    postgres_db: str
    postgres_user: str
    postgres_password: str

    class Config:
        env_file = ".env"

    @property
    def effective_worker_api_key(self) -> str:
        return self.worker_api_key or self.api_key

    @property
    def database_url(self) -> str:
        from urllib.parse import quote_plus
        return (
            f"postgresql+asyncpg://"
            f"{quote_plus(self.postgres_user)}:"
            f"{quote_plus(self.postgres_password)}@"
            f"{self.postgres_host}:"
            f"{self.postgres_port}/"
            f"{self.postgres_db}"
        )

settings = Settings()
