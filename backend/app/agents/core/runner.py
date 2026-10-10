import logging
import time
import uuid
from typing import Any, TypeVar

from opentelemetry import trace
from pydantic_ai import Agent
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.usage import RunUsage, UsageLimits
from sqlalchemy.orm import Session

from app.agents.core.models import ModelHandle
from app.config import get_settings
from app.models import AIRun, AIRunStatus
from app.repositories import ai_run_repo

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

T = TypeVar("T")


class AIRunError(Exception):
    """An agent run failed (provider error, or output still invalid after all retries)."""


class AIBudgetExceeded(AIRunError):
    """The user's daily token budget is used up, or this run would push it over."""


def run_agent(
    db: Session,
    agent: Agent[Any, T],
    prompt: str,
    *,
    feature: str,
    model: ModelHandle,
    user_id: uuid.UUID | None,
    max_retries: int,
    deps: Any = None,
) -> T:
    """Run an agent synchronously with the daily token budget enforced, and record an ai_runs row
    (tokens, latency, status, trace id) whether the run succeeds or fails.

    Output validation, including the domain-rule model_validators on the output type, happens
    inside the agent: a failing output is sent back to the model with the error, up to
    `max_retries` times.
    """
    settings = get_settings()
    usage_limits = UsageLimits()
    if settings.ai_daily_token_budget > 0:
        remaining = settings.ai_daily_token_budget - ai_run_repo.tokens_used_today(db, user_id)
        if remaining <= 0:
            _record(db, feature, model, user_id, AIRunStatus.BUDGET_EXCEEDED, RunUsage(), 0, None,
                    "Daily token budget already used up")
            raise AIBudgetExceeded("Daily AI token budget used up. It resets at 00:00 UTC.")
        # Caps a single run (including its retries) so it can't overshoot the budget by much.
        usage_limits = UsageLimits(total_tokens_limit=remaining)

    # Passed in rather than read from the result so usage from a failed run is still recorded.
    usage = RunUsage()
    started = time.perf_counter()
    with tracer.start_as_current_span(f"ai_run {feature}") as span:
        span.set_attribute("app.feature", feature)
        context = span.get_span_context()
        trace_id = format(context.trace_id, "032x") if context.is_valid else None
        try:
            result = agent.run_sync(
                prompt,
                model=model.model,
                deps=deps,
                retries={"output": max_retries},
                usage=usage,
                usage_limits=usage_limits,
            )
        except UsageLimitExceeded as exc:
            _record(db, feature, model, user_id, AIRunStatus.BUDGET_EXCEEDED, usage, _elapsed_ms(started),
                    trace_id, str(exc))
            raise AIBudgetExceeded("This request would exceed today's AI token budget.") from exc
        except Exception as exc:  # noqa: BLE001 - every provider/validation failure is recorded, then re-raised
            logger.warning("Agent run %s failed: %s", feature, exc)
            _record(db, feature, model, user_id, AIRunStatus.FAILED, usage, _elapsed_ms(started), trace_id,
                    str(exc))
            raise AIRunError(str(exc)) from exc

    _record(db, feature, model, user_id, AIRunStatus.SUCCEEDED, usage, _elapsed_ms(started), trace_id, None)
    return result.output


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _record(
    db: Session,
    feature: str,
    model: ModelHandle,
    user_id: uuid.UUID | None,
    status: AIRunStatus,
    usage: RunUsage,
    latency_ms: int,
    trace_id: str | None,
    error_message: str | None,
) -> None:
    ai_run_repo.create_run(
        db,
        AIRun(
            user_id=user_id,
            feature=feature,
            provider=model.provider,
            model_name=model.model_name,
            status=status,
            requests=usage.requests,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            latency_ms=latency_ms,
            trace_id=trace_id,
            error_message=error_message,
        ),
    )
