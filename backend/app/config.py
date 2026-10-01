from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://app:app@localhost:5432/language_learning_hub"

    ai_provider: Literal["gemini", "ollama"] = "gemini"
    ai_json_max_retries: int = 2

    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-lite-latest"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma2:9b"

    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
