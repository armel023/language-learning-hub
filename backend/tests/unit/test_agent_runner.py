import uuid

import pytest
from pydantic import BaseModel, model_validator
from pydantic_ai import Agent, NativeOutput
from pydantic_ai.messages import ModelResponse, RetryPromptPart, TextPart
from pydantic_ai.models.function import FunctionModel

from app.agents.core import runner
from app.agents.core.models import ModelHandle
from app.agents.core.runner import AIBudgetExceeded, AIRunError, run_agent
from app.config import get_settings
from app.models import AIRunStatus


class Greeting(BaseModel):
    message: str

    @model_validator(mode="after")
    def must_be_german(self) -> "Greeting":
        if self.message != "hallo":
            raise ValueError("message must be 'hallo'")
        return self


agent = Agent(output_type=NativeOutput(Greeting))


def scripted_model(*replies: str) -> tuple[ModelHandle, list]:
    """A FunctionModel that returns the given replies in order and records each request."""
    remaining = list(replies)
    requests = []

    def respond(messages, info):
        requests.append(messages[-1])
        return ModelResponse(parts=[TextPart(remaining.pop(0))])

    return ModelHandle(model=FunctionModel(respond), provider="gemini", model_name="fake"), requests


@pytest.fixture
def recorded_runs(monkeypatch):
    runs = []
    monkeypatch.setattr(runner.ai_run_repo, "create_run", lambda db, run: runs.append(run))
    monkeypatch.setattr(runner.ai_run_repo, "tokens_used_today", lambda db, user_id: 0)
    return runs


def run(model: ModelHandle, max_retries: int = 2):
    return run_agent(None, agent, "hi", feature="test", model=model, user_id=uuid.uuid4(), max_retries=max_retries)


def test_success_returns_output_and_records_usage(recorded_runs):
    model, _ = scripted_model('{"message": "hallo"}')
    assert run(model).message == "hallo"

    [record] = recorded_runs
    assert record.status == AIRunStatus.SUCCEEDED
    assert record.feature == "test"
    assert record.provider == "gemini"
    assert record.requests == 1
    assert record.total_tokens > 0
    assert record.total_tokens == record.input_tokens + record.output_tokens


def test_invalid_json_is_retried_with_the_error_fed_back(recorded_runs):
    model, requests = scripted_model("not json", '{"message": "hallo"}')
    assert run(model).message == "hallo"
    assert any(isinstance(part, RetryPromptPart) for part in requests[1].parts)
    assert recorded_runs[0].requests == 2


def test_domain_rule_validator_failure_is_retried(recorded_runs):
    model, requests = scripted_model('{"message": "hello"}', '{"message": "hallo"}')
    assert run(model).message == "hallo"
    retry = next(p for p in requests[1].parts if isinstance(p, RetryPromptPart))
    assert "must be 'hallo'" in str(retry.content)


def test_exhausted_retries_raise_and_still_record_tokens(recorded_runs):
    model, _ = scripted_model("bad", "still bad", "still bad")
    with pytest.raises(AIRunError):
        run(model, max_retries=2)

    [record] = recorded_runs
    assert record.status == AIRunStatus.FAILED
    assert record.requests == 3
    assert record.total_tokens > 0
    assert record.error_message


def test_budget_already_used_up_blocks_the_call(monkeypatch, recorded_runs):
    monkeypatch.setattr(runner.ai_run_repo, "tokens_used_today", lambda db, user_id: 10**9)
    model, requests = scripted_model('{"message": "hallo"}')

    with pytest.raises(AIBudgetExceeded):
        run(model)
    assert requests == []
    assert recorded_runs[0].status == AIRunStatus.BUDGET_EXCEEDED


def test_run_is_capped_at_remaining_budget(monkeypatch, recorded_runs):
    budget = get_settings().ai_daily_token_budget
    monkeypatch.setattr(runner.ai_run_repo, "tokens_used_today", lambda db, user_id: budget - 5)
    model, _ = scripted_model('{"message": "hallo"}')

    with pytest.raises(AIBudgetExceeded):
        run(model)
    assert recorded_runs[0].status == AIRunStatus.BUDGET_EXCEEDED
    assert recorded_runs[0].total_tokens > 5


def test_zero_budget_means_unlimited(monkeypatch, recorded_runs):
    monkeypatch.setattr(get_settings(), "ai_daily_token_budget", 0)
    monkeypatch.setattr(
        runner.ai_run_repo, "tokens_used_today", lambda db, user_id: pytest.fail("budget should not be queried")
    )
    model, _ = scripted_model('{"message": "hallo"}')
    assert run(model).message == "hallo"
