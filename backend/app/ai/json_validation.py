from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.ai.base import AIProvider

T = TypeVar("T", bound=BaseModel)


class AIGenerationError(Exception):
    pass


def generate_validated(
    provider: AIProvider,
    system_prompt: str,
    user_prompt: str,
    response_schema: type[T],
    max_retries: int = 2,
) -> T:
    """Call the provider and validate its JSON output against response_schema, retrying
    with the validation error fed back to the model if it doesn't conform. This also
    enforces any domain-rule validators (model_validator) declared on response_schema,
    since model_validate_json runs them the same way as field validation."""
    prompt = user_prompt
    last_error: ValidationError | None = None

    for _ in range(max_retries + 1):
        raw = provider.generate_raw(system_prompt, prompt, response_schema)
        try:
            return response_schema.model_validate_json(raw)
        except ValidationError as exc:
            last_error = exc
            prompt = (
                f"{user_prompt}\n\nYour previous response was invalid JSON for the required "
                f"schema. Validation errors:\n{exc}\n\nReturn ONLY corrected JSON, "
                "no commentary, matching the schema exactly."
            )

    raise AIGenerationError(
        f"AI failed to produce valid JSON matching {response_schema.__name__} "
        f"after {max_retries + 1} attempt(s): {last_error}"
    )
