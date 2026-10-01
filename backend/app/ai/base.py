from typing import Protocol

from pydantic import BaseModel


class AIProvider(Protocol):
    def generate_raw(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel] | None = None,
    ) -> str:
        """Return raw text from the model. response_schema is a hint providers may use
        for native structured-output support; callers still validate the result themselves."""
        ...
