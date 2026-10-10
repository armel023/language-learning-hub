from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://app:app@localhost:5432/language_learning_hub"

    ai_provider: Literal["gemini", "ollama"] = "gemini"
    ai_json_max_retries: int = 2
    # Per-user tokens per UTC day across all agent runs; 0 disables the budget.
    ai_daily_token_budget: int = 1_000_000

    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-lite-latest"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma2:9b"

    cors_origins: str = "http://localhost:5173"

    max_upload_bytes: int = 10 * 1024 * 1024

    # Background agent jobs (in-process thread pool). Inline mode runs jobs synchronously
    # inside enqueue(), for tests and debugging.
    jobs_max_workers: int = 4
    jobs_run_inline: bool = False

    # Self-hosted trace backend (Arize Phoenix), e.g. http://phoenix:6006/v1/traces. Empty = off.
    otel_exporter_otlp_endpoint: str = ""
    otel_service_name: str = "a2-deutsch-hub-backend"
    # Include prompts/completions in traces. Fine for a personal, self-hosted setup.
    otel_include_content: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
