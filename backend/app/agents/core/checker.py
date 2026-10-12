"""Independent checker for generated exercises with an answer key (Lesen, Hören).

It sees what the student gets (never the answer key; for Hören, the transcript of the audio),
solves every item, and flags problems. The flow compares its answers with the generator's key: a disagreement usually means
the item is ambiguous or the key is wrong, which is the failure a learner can't detect.
"""
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, NativeOutput, RunContext

IssueKind = Literal[
    "ambiguous",  # more than one option could be defended
    "no_correct_option",  # nothing in the text supports any option
    "above_a2",  # vocabulary or grammar too hard for A2
    "verbatim",  # correct option copies the text word for word (keyword matching, not reading)
    "other",
]


class CheckedAnswer(BaseModel):
    item_number: int = Field(description="question_number or aufgabe_number")
    answer: str
    reason: str = Field(description="One short sentence quoting or paraphrasing the deciding detail.")


class CheckerIssue(BaseModel):
    item_number: int | None = Field(description="The affected item, or null for the whole exercise.")
    kind: IssueKind
    detail: str
    blocking: bool = Field(description="True if a student could not reliably get this item right.")


class CheckerReport(BaseModel):
    answers: list[CheckedAnswer]
    issues: list[CheckerIssue] = Field(default_factory=list)


INSTRUCTIONS = """You are reviewing a Goethe-Zertifikat A2 exercise before students see it.

First, solve it exactly as a careful A2 candidate would: use ONLY the information in the
exercise, decide each item on its own, and do not guess what the author intended. The "Beispiel"
is already solved for the student; do not answer it. For a listening (Hören) exercise you get the
transcript of the audio instead of the audio: answer from what is said in it.

Then report problems you noticed while solving. Mark an issue as blocking only when a student
who understood the text could still reasonably pick a different answer, or could not find any
supported answer, or when the language is clearly above A2. Minor style remarks are not
blocking. Do not invent issues: an exercise with none is the normal case."""


@dataclass(frozen=True)
class CheckerDeps:
    allowed_answers: tuple[str, ...]
    item_numbers: tuple[int, ...]


checker_agent = Agent(
    name="exercise_checker",
    deps_type=CheckerDeps,
    output_type=NativeOutput(CheckerReport),
    instructions=INSTRUCTIONS,
)


def normalize_answer(raw: str, allowed: tuple[str, ...]) -> str | None:
    """Map what the model wrote ('b', '"B"', 'B.', 'Option B') onto one allowed answer, or None."""
    junk = " \t\n\"'.,:;()"
    text = raw.strip(junk)
    if text.lower().startswith("option "):
        text = text[len("option "):].strip(junk)
    by_lower = {a.lower(): a for a in allowed}
    return by_lower.get(text.lower())


@checker_agent.output_validator
def _answers_are_well_formed(ctx: RunContext[CheckerDeps], report: CheckerReport) -> CheckerReport:
    allowed = ctx.deps.allowed_answers
    for answer in report.answers:
        canonical = normalize_answer(answer.answer, allowed)
        if canonical is None:
            raise ModelRetry(
                f"Item {answer.item_number}: {answer.answer!r} is not a valid answer. "
                f"Answer with exactly one of: {', '.join(allowed)}."
            )
        answer.answer = canonical
    missing = sorted(set(ctx.deps.item_numbers) - {a.item_number for a in report.answers})
    if missing:
        raise ModelRetry(f"Answer every item. Missing: {missing}.")
    return report
