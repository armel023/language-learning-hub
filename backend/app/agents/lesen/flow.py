"""Generate -> check -> revise loop for Lesen exercises (evaluator-optimizer pattern).

Orchestration is plain code, not an LLM: the generator drafts, the checker solves the draft
blind, and the code decides whether they agree. Disagreements and blocking issues go back to
the generator as concrete revision notes, up to `max_revisions` times.
"""
import json
import uuid
from dataclasses import dataclass, field

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.core.models import ModelHandle
from app.agents.core.runner import run_agent
from app.agents.lesen.checker import CheckerDeps, CheckerReport, checker_agent
from app.agents.lesen.specs import TeilSpec


@dataclass(frozen=True)
class RunContext:
    db: Session
    model: ModelHandle
    user_id: uuid.UUID | None
    max_retries: int


@dataclass
class GenerationResult:
    output: BaseModel
    content: dict
    answer_key: dict
    verified: bool
    rounds: list[dict] = field(default_factory=list)

    def meta(self) -> dict:
        """Stored on the exercise (generation_meta) for later evals and debugging."""
        return {"verified": self.verified, "rounds": self.rounds}


class UnverifiedExercise(Exception):
    """The checker still disagreed with the generator after every allowed revision."""

    def __init__(self, result: GenerationResult):
        super().__init__("Could not produce an exercise the independent checker agreed with.")
        self.result = result


def generate_checked(
    ctx: RunContext,
    spec: TeilSpec,
    topic: str | None,
    level: str,
    max_revisions: int,
    require_verification: bool = True,
) -> GenerationResult:
    base_prompt = spec.build_prompt(topic, level)
    prompt = base_prompt
    rounds: list[dict] = []

    for round_number in range(max_revisions + 1):
        output = run_agent(
            ctx.db, spec.generator, prompt, feature=f"lesen_teil{spec.teil}",
            model=ctx.model, user_id=ctx.user_id, max_retries=ctx.max_retries,
        )
        content, answer_key = spec.split(output)
        checker_deps = CheckerDeps(
            allowed_answers=spec.allowed_answers,
            item_numbers=tuple(int(item) for item in answer_key["answers"]),
        )
        report = run_agent(
            ctx.db, checker_agent, _checker_prompt(spec, content), feature=f"lesen_teil{spec.teil}_check",
            model=ctx.model, user_id=ctx.user_id, max_retries=ctx.max_retries, deps=checker_deps,
        )
        problems = find_problems(spec, answer_key, report)
        rounds.append({"round": round_number, "problems": problems})
        result = GenerationResult(output, content, answer_key, verified=not problems, rounds=rounds)
        if result.verified:
            return result
        prompt = _revision_prompt(base_prompt, output, problems)

    if require_verification:
        raise UnverifiedExercise(result)
    return result


def find_problems(spec: TeilSpec, answer_key: dict, report: CheckerReport) -> list[str]:
    """Human-readable problems: answer mismatches between key and checker, plus blocking issues.

    The checker's answers are already canonical (its output validator enforces the allowed set);
    the key is converted into the same vocabulary before comparing.
    """
    expected: dict[str, int | str] = answer_key["answers"]
    given = {str(a.item_number): a for a in report.answers}
    problems: list[str] = []

    for item, correct in sorted(expected.items()):
        checked = given.get(item)
        if checked is None:
            problems.append(f"Item {item}: the reviewer could not answer it.")
        elif checked.answer != spec.key_to_answer(correct):
            problems.append(
                f"Item {item}: answer key says {_describe_key(spec, correct)}, but an independent "
                f"reviewer chose {checked.answer!r} because: {checked.reason}"
            )

    for issue in report.issues:
        if issue.blocking:
            where = f"Item {issue.item_number}" if issue.item_number is not None else "Whole exercise"
            problems.append(f"{where} ({issue.kind}): {issue.detail}")
    return problems


def _describe_key(spec: TeilSpec, correct: int | str) -> str:
    label = spec.key_to_answer(correct)
    # Name both forms so the generator can relate the note to its own correct_option_index.
    return repr(label) if label == str(correct) else f"{label!r} (correct_option_index {correct})"


def _checker_prompt(spec: TeilSpec, content: dict) -> str:
    return (
        f"Lesen Teil {spec.teil} exercise, exactly as the student sees it:\n"
        f"{json.dumps(content, ensure_ascii=False, indent=2)}\n\n"
        f"How to write each answer: {spec.answer_format}"
    )


def _revision_prompt(base_prompt: str, previous: BaseModel, problems: list[str]) -> str:
    notes = "\n".join(f"- {p}" for p in problems)
    return (
        f"{base_prompt}\n\n"
        "Here is your previous draft:\n"
        f"{previous.model_dump_json(indent=2)}\n\n"
        "An independent reviewer solved it without seeing the answer key and found these problems:\n"
        f"{notes}\n\n"
        "Return a corrected, complete exercise. Fix these problems so every item has exactly one "
        "clearly correct answer that matches your answer key. Keep everything that was fine."
    )
