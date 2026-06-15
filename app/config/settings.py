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

    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # How many semantically relevant messages added to context (same chat)
    context_semantic_limit: int = 4
    # How many cross-chat memories to include (0 = disabled)
    cross_chat_semantic_limit: int = 2

    # Seconds of silence after which a participant's chain is auto-closed
    chain_gap_seconds: int = 5

    # Embedding worker
    embedding_worker_poll_interval: float = 2.0
    embedding_job_max_attempts: int = 3
    # Set to false on API instances when running worker as a separate service
    worker_enabled: bool = True

    api_key: str

    postgres_host: str
    postgres_port: int

    postgres_db: str
    postgres_user: str
    postgres_password: str

    class Config:
        env_file = ".env"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.postgres_user}:"
            f"{self.postgres_password}@"
            f"{self.postgres_host}:"
            f"{self.postgres_port}/"
            f"{self.postgres_db}"
        )

settings = Settings()
