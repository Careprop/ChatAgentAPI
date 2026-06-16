from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-5.4-mini"

    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # Token budget for L1 chat history (approx 1 token = 4 chars)
    context_history_tokens: int = 4_000
    # How many facts to include in context per user / per chat
    context_facts_limit: int = 10
    # Hard cap on stored personal facts per user per chat (oldest deleted when exceeded)
    facts_per_user_limit: int = 20
    # Hard cap on stored chat facts per chat (oldest deleted when exceeded)
    chat_facts_per_chat_limit: int = 20

    # Max simultaneous in-flight send_message requests per chat
    max_chat_concurrent: int = 5
    # Rolling window duration for per-user token budget (hours)
    token_window_hours: int = 4

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
