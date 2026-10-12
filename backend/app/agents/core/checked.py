"""Generate -> check -> revise loop for exercises with an objective answer key
(evaluator-optimizer pattern), shared by Lesen and Hören.

Orchestration is plain code, not an LLM: the generator drafts, the checker solves the draft
blind, and the code decides whether they agree. Disagreements and blocking issues go back to
the generator as concrete revision notes, up to `max_revisions` times.
"""
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from pydantic import BaseModel
from pydantic_ai import Agent
from sqlalchemy.orm import Session

from app.agents.core.checker import CheckerDeps, CheckerReport, checker_agent
from app.agents.core.models import ModelHandle
from app.agents.core.runner import run_agent


@dataclass(frozen=True)
class TeilSpec:
    """Everything that differs between Teile; the flow below is the same for all of them."""

    teil: int
    generator: Agent
    build_prompt: Callable[[str | None, str], str]
    # AI output -> (content shown to the student, answer key with answers + explanations)
    split: Callable[[BaseModel], tuple[dict, dict]]
    title: Callable[[BaseModel, str | None], str]
    # Tells the checker how to write each answer.
    answer_format: str
    # The only answers the checker may give, and how an answer-key value maps onto them.
    # Letters rather than 0-based indexes: small local models tend to count options from 1.
    allowed_answers: tuple[str, ...]
    key_to_answer: Callable[[int | str], str]
    skill: str = "lesen"
    # What the checker is shown; defaults to the student-visible content. Hören adds the
    # transcript here, since the checker can't listen to audio.
    checker_view: Callable[[BaseModel, dict], dict] | None = None


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
            ctx.db, spec.generator, prompt, feature=f"{spec.skill}_teil{spec.teil}",
            model=ctx.model, user_id=ctx.user_id, max_retries=ctx.max_retries,
        )
        content, answer_key = spec.split(output)
        checker_deps = CheckerDeps(
            allowed_answers=spec.allowed_answers,
            item_numbers=tuple(int(item) for item in answer_key["answers"]),
        )
        view = spec.checker_view(output, content) if spec.checker_view else content
        report = run_agent(
            ctx.db, checker_agent, _checker_prompt(spec, view), feature=f"{spec.skill}_teil{spec.teil}_check",
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


def _checker_prompt(spec: TeilSpec, view: dict) -> str:
    what = "exactly as the student sees it" if spec.skill == "lesen" else "with the transcript of the audio"
    return (
        f"{spec.skill.capitalize()} Teil {spec.teil} exercise, {what}:\n"
        f"{json.dumps(view, ensure_ascii=False, indent=2)}\n\n"
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
