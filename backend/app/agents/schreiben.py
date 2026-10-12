"""Schreiben: a task generator and a rubric grader.

The grader is a structured-output agent with per-run dependencies: the task's content points
and the student's weak words are injected into its instructions, and an output validator
rejects grades that don't match the task (wrong number of points, out-of-order numbering),
sending the model back with the reason. No tools are needed, so it also runs on local models
without tool calling.
"""
from dataclasses import dataclass, field

from pydantic_ai import Agent, ModelRetry, NativeOutput, RunContext

from app.schemas.schreiben import SchreibenGradeAI, SchreibenTaskAI


@dataclass(frozen=True)
class SchreibenSpec:
    teil: int
    kind: str
    register: str
    word_range: tuple[int, int]
    content_points: int


SPECS: dict[int, SchreibenSpec] = {
    1: SchreibenSpec(teil=1, kind="a short informal message (SMS or chat) to a friend or family member",
                     register="informal", word_range=(20, 30), content_points=3),
    2: SchreibenSpec(teil=2, kind="a short semi-formal email to a teacher, landlord, colleague or office",
                     register="formal", word_range=(30, 40), content_points=3),
}

# Practice rubric modelled on the Goethe A2 criteria (task completion, communicative design,
# accuracy). Not the official weighting: each content point and each criterion is 0-2 points.
CRITERION_MAX = 2


def max_score(spec: SchreibenSpec) -> int:
    return CRITERION_MAX * (spec.content_points + 2)


# --- generator ---------------------------------------------------------------------------

GENERATOR_INSTRUCTIONS = """You write Schreiben tasks for the Goethe-Zertifikat A2 exam.

A task describes an everyday situation and asks the student to write a short message about
it. The content points are what the message must cover: concrete, distinct things to say
(e.g. "Entschuldigen Sie sich.", "Nennen Sie einen neuen Termin.", "Fragen Sie nach ..."),
phrased as short German instructions. Each point must require its own sentence; no point may
be answered by another. Everything must be simple A2 German. Do not write the answer."""

generator_agent = Agent(
    name="schreiben_generator",
    deps_type=SchreibenSpec,
    output_type=NativeOutput(SchreibenTaskAI),
    instructions=GENERATOR_INSTRUCTIONS,
)


@generator_agent.output_validator
def _matches_spec(ctx: RunContext[SchreibenSpec], task: SchreibenTaskAI) -> SchreibenTaskAI:
    spec = ctx.deps
    if len(task.content_points) != spec.content_points:
        raise ModelRetry(f"Give exactly {spec.content_points} content points, not {len(task.content_points)}.")
    if task.formality != spec.register:
        raise ModelRetry(f"This Teil needs the {spec.register} register.")
    return task


def build_generator_prompt(spec: SchreibenSpec, topic: str | None, level: str) -> str:
    low, high = spec.word_range
    topic_line = f"Topic: {topic}" if topic else "Topic: pick an everyday A2 situation (appointments, invitations, plans, problems at home or work)."
    return (
        f"Write a {level} Schreiben Teil {spec.teil} task: {spec.kind}.\n"
        f"Register: {spec.register}. Exactly {spec.content_points} content points. "
        f"The student will write {low}-{high} words.\n{topic_line}"
    )


# --- grader ------------------------------------------------------------------------------


@dataclass(frozen=True)
class GradingDeps:
    task: SchreibenTaskAI
    spec: SchreibenSpec
    word_count: int
    weak_words: list[str] = field(default_factory=list)


GRADER_INSTRUCTIONS = """You are a fair, encouraging examiner grading a Goethe-Zertifikat A2 Schreiben answer.

Grade only what the student wrote, against the task. Score each content point 0-2:
0 = not addressed, 1 = addressed but incomplete or hard to understand, 2 = clearly addressed.
Communication 0-2: greeting and closing, correct register, the text hangs together and suits
the recipient. Accuracy 0-2: judge errors by whether they hinder understanding; A2 learners
are expected to make some mistakes, so a text with small errors that is fully clear earns 2.

Corrections: pick the most useful ones (at most 6), quote the student's exact words, and
explain the rule simply. The improved version must keep the student's ideas and stay at A2."""

grader_agent = Agent(
    name="schreiben_grader",
    deps_type=GradingDeps,
    output_type=NativeOutput(SchreibenGradeAI),
    instructions=GRADER_INSTRUCTIONS,
)


@grader_agent.instructions
def _task_context(ctx: RunContext[GradingDeps]) -> str:
    deps = ctx.deps
    low, high = deps.spec.word_range
    points = "\n".join(f"{i}. {p}" for i, p in enumerate(deps.task.content_points, start=1))
    lines = [
        f"Task (Teil {deps.spec.teil}, {deps.task.formality} register, to {deps.task.recipient}):",
        deps.task.situation,
        f"Content points:\n{points}",
        f"Target length: {low}-{high} words. The student wrote {deps.word_count} words "
        "(length alone never costs more than 1 point on communication).",
    ]
    if deps.weak_words:
        lines.append(
            "Words this student often gets wrong in flashcard practice: "
            + ", ".join(deps.weak_words)
            + ". If they used any of these incorrectly, include that among the corrections."
        )
    return "\n\n".join(lines)


@grader_agent.output_validator
def _matches_task(ctx: RunContext[GradingDeps], grade: SchreibenGradeAI) -> SchreibenGradeAI:
    expected = list(range(1, len(ctx.deps.task.content_points) + 1))
    got = sorted(p.point_number for p in grade.content_points)
    if got != expected:
        raise ModelRetry(f"Grade every content point exactly once, numbered {expected}; you returned {got}.")
    grade.content_points.sort(key=lambda p: p.point_number)
    return grade


def build_grader_prompt(response_text: str) -> str:
    return f"The student's answer:\n\n{response_text}"


def count_words(text: str) -> int:
    return len(text.split())
