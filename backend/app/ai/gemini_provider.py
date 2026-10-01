from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import Settings


class GeminiProvider:
    def __init__(self, settings: Settings):
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model

    def generate_raw(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel] | None = None,
    ) -> str:
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=response_schema,
        )
        response = self._client.models.generate_content(
            model=self._model,
            contents=user_prompt,
            config=config,
        )
        return response.text
