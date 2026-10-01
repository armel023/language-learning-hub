from functools import lru_cache

from app.ai.base import AIProvider
from app.ai.gemini_provider import GeminiProvider
from app.ai.ollama_provider import OllamaProvider
from app.config import get_settings


@lru_cache
def get_ai_provider() -> AIProvider:
    settings = get_settings()
    if settings.ai_provider == "ollama":
        return OllamaProvider(settings)
    return GeminiProvider(settings)
