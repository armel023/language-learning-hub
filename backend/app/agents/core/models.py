from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from pydantic_ai.models import Model
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.ollama import OllamaProvider

from app.config import Settings, get_settings

ProviderName = Literal["gemini", "ollama"]


@dataclass(frozen=True)
class ModelHandle:
    """The configured model plus the labels we record alongside each run (ai_runs, generated_by)."""

    model: Model
    provider: ProviderName
    model_name: str


def build_model(settings: Settings) -> ModelHandle:
    if settings.ai_provider == "ollama":
        # Ollama is reached through its OpenAI-compatible API, which lives under /v1.
        base_url = settings.ollama_base_url.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        model = OllamaModel(settings.ollama_model, provider=OllamaProvider(base_url=base_url))
        return ModelHandle(model=model, provider="ollama", model_name=settings.ollama_model)

    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    model = GoogleModel(settings.gemini_model, provider=GoogleProvider(api_key=settings.gemini_api_key))
    return ModelHandle(model=model, provider="gemini", model_name=settings.gemini_model)


@lru_cache
def get_model() -> ModelHandle:
    """FastAPI dependency. Override it in tests to inject a FunctionModel/TestModel."""
    return build_model(get_settings())
