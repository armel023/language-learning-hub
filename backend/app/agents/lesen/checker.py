"""Independent checker for generated Lesen exercises.

It sees exactly what the student sees (never the answer key), solves every item, and flags
problems. The flow compares its answers with the generator's key: a disagreement usually means
the item is ambiguous or the key is wrong, which is the failure a learner can't detect.
"""
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent, NativeOutput

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


INSTRUCTIONS = """You are reviewing a Goethe-Zertifikat A2 Lesen exercise before students see it.

First, solve it exactly as a careful A2 candidate would: use ONLY the information in the
exercise, decide each item on its own, and do not guess what the author intended. The "Beispiel"
is already solved for the student; do not answer it.

Then report problems you noticed while solving. Mark an issue as blocking only when a student
who understood the text could still reasonably pick a different answer, or could not find any
supported answer, or when the language is clearly above A2. Minor style remarks are not
blocking. Do not invent issues: an exercise with none is the normal case."""

checker_agent = Agent(
    name="lesen_checker",
    output_type=NativeOutput(CheckerReport),
    instructions=INSTRUCTIONS,
)
