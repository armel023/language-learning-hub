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

    # Lesen/Hören: how many times the generator may revise a draft the checker disagreed with,
    # and whether a still-unverified exercise is rejected (True) or saved with verified=false.
    exercise_max_revisions: int = 1
    exercise_require_verification: bool = True

    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-lite-latest"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"
    # Small local models under JSON-schema constrained decoding can fall into repetition loops.
    # A repetition penalty avoids most of them; the token cap makes the rest fail in minutes,
    # not after the model hits Ollama's own repeat limit. 2048 fits a full Lesen exercise.
    ollama_max_tokens: int = 2048
    ollama_temperature: float = 0.7
    ollama_frequency_penalty: float = 0.3

    # Hören audio. Piper runs offline from voice models baked into the backend image; Gemini TTS
    # is online and more natural. Each speaker in a script gets its own voice from these lists.
    tts_provider: Literal["piper", "gemini"] = "piper"
    piper_voices_dir: str = "/opt/piper-voices"
    piper_female_voices: str = "de_DE-kerstin-low,de_DE-ramona-low"
    piper_male_voices: str = "de_DE-thorsten-medium,de_DE-karlsson-low"
    # >1 speaks slower; A2 listening material is a little slower than natural speech.
    piper_length_scale: float = 1.1
    gemini_tts_model: str = "gemini-3.8-flash-lite-tts"
    gemini_tts_female_voices: str = "Kore,Leda"
    gemini_tts_male_voices: str = "Puck,Charon"
    # Generated media (Hören audio) lives here and is served under /api/v1/media.
    media_dir: str = "/data/media"

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
