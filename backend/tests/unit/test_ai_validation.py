import pytest
from pydantic import BaseModel

from app.ai.json_validation import AIGenerationError, generate_validated


class Greeting(BaseModel):
    message: str


class FakeProvider:
    def __init__(self, responses: list[str]):
        self._responses = responses
        self.calls = 0

    def generate_raw(self, system_prompt, user_prompt, response_schema=None):
        response = self._responses[self.calls]
        self.calls += 1
        return response


def test_generate_validated_succeeds_first_try():
    provider = FakeProvider(['{"message": "hallo"}'])
    result = generate_validated(provider, "system", "user", Greeting)
    assert result.message == "hallo"
    assert provider.calls == 1


def test_generate_validated_retries_then_succeeds():
    provider = FakeProvider(["not json", '{"message": "hallo"}'])
    result = generate_validated(provider, "system", "user", Greeting, max_retries=2)
    assert result.message == "hallo"
    assert provider.calls == 2


def test_generate_validated_raises_after_exhausting_retries():
    provider = FakeProvider(["bad", "still bad", "still bad"])
    with pytest.raises(AIGenerationError):
        generate_validated(provider, "system", "user", Greeting, max_retries=2)
    assert provider.calls == 3
