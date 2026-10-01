import ollama
from pydantic import BaseModel

from app.config import Settings


class OllamaProvider:
    def __init__(self, settings: Settings):
        self._client = ollama.Client(host=settings.ollama_base_url)
        self._model = settings.ollama_model

    def generate_raw(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel] | None = None,
    ) -> str:
        # Ollama's JSON mode is weaker than Gemini's native structured output, so we also
        # spell the schema out in the prompt as a belt-and-suspenders measure.
        if response_schema is not None:
            system_prompt = (
                f"{system_prompt}\n\nRespond with JSON matching exactly this schema:\n"
                f"{response_schema.model_json_schema()}"
            )

        response = self._client.chat(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            format="json",
        )
        return response["message"]["content"]
