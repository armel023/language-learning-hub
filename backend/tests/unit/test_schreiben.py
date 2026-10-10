import json
import uuid
from types import SimpleNamespace

import pytest
from pydantic_ai.messages import ModelResponse, RetryPromptPart, TextPart
from pydantic_ai.models.function import FunctionModel

from app.agents import schreiben
from app.agents.core import runner
from app.agents.core.models import ModelHandle
from app.agents.core.runner import AIRunError
from app.jobs.runner import JobFailed
from app.models import AttemptStatus
from app.services import schreiben_service

TASK = {
    "title": "Verspätung",
    "situation": "Sie kommen heute zu spät zum Deutschkurs.",
    "recipient": "Ihre Freundin Anna",
    "formality": "informal",
    "content_points": ["Entschuldigen Sie sich.", "Nennen Sie den Grund.", "Machen Sie einen Vorschlag."],
}


def grade(points=(2, 1, 2), communication=2, accuracy=1) -> dict:
    return {
        "content_points": [{"point_number": i, "score": s, "comment": "ok"} for i, s in enumerate(points, start=1)],
        "communication": {"score": communication, "comment": "ok"},
        "accuracy": {"score": accuracy, "comment": "ok"},
        "corrections": [{"original": "ich komme spät", "corrected": "ich komme zu spät", "explanation": "zu spät = late"}],
        "summary": "Gut gemacht.",
        "improved_version": "Hallo Anna, ...",
    }


@pytest.fixture(autouse=True)
def no_db(monkeypatch):
    monkeypatch.setattr(runner.ai_run_repo, "create_run", lambda db, run: None)
    monkeypatch.setattr(runner.ai_run_repo, "tokens_used_today", lambda db, user_id: 0)


def scripted(*bodies):
    remaining = list(bodies)
    seen = []

    def respond(messages, info):
        seen.append((messages, info))
        return ModelResponse(parts=[TextPart(json.dumps(remaining.pop(0)))])

    return ModelHandle(FunctionModel(respond), "gemini", "fake"), seen


def run(agent, model, prompt, deps):
    return runner.run_agent(None, agent, prompt, feature="t", model=model, user_id=None, max_retries=2, deps=deps)


def test_max_score_is_two_points_per_point_and_criterion():
    assert schreiben.max_score(schreiben.SPECS[1]) == 10
    assert schreiben.max_score(schreiben.SPECS[2]) == 10


def test_generator_retries_when_point_count_is_wrong():
    model, seen = scripted({**TASK, "content_points": TASK["content_points"][:2]}, TASK)
    task = run(schreiben.generator_agent, model, "go", schreiben.SPECS[1])
    assert len(task.content_points) == 3
    retry = next(p for p in seen[1][0][-1].parts if isinstance(p, RetryPromptPart))
    assert "exactly 3 content points" in str(retry.content)


def test_generator_retries_when_register_is_wrong():
    model, seen = scripted({**TASK, "formality": "formal"}, TASK)
    assert run(schreiben.generator_agent, model, "go", schreiben.SPECS[1]).formality == "informal"
    assert len(seen) == 2


def deps(weak_words=()):
    return schreiben.GradingDeps(
        task=schreiben.SchreibenTaskAI.model_validate(TASK),
        spec=schreiben.SPECS[1],
        word_count=24,
        weak_words=list(weak_words),
    )


def test_grader_retries_when_a_content_point_is_missing_and_sorts_points():
    incomplete = grade()
    incomplete["content_points"] = incomplete["content_points"][:2]
    shuffled = grade()
    shuffled["content_points"].reverse()
    model, seen = scripted(incomplete, shuffled)

    result = run(schreiben.grader_agent, model, "answer", deps())
    assert [p.point_number for p in result.content_points] == [1, 2, 3]
    retry = next(p for p in seen[1][0][-1].parts if isinstance(p, RetryPromptPart))
    assert "[1, 2, 3]" in str(retry.content)


def test_grader_instructions_include_task_word_count_and_weak_words():
    model, seen = scripted(grade())
    run(schreiben.grader_agent, model, "answer", deps(weak_words=["Termin", "verschieben"]))
    instructions = seen[0][1].instructions
    assert "Machen Sie einen Vorschlag." in instructions
    assert "wrote 24 words" in instructions
    assert "Termin, verschieben" in instructions


def test_grader_omits_weak_words_line_when_there_are_none():
    model, seen = scripted(grade())
    run(schreiben.grader_agent, model, "answer", deps())
    assert "often gets wrong" not in seen[0][1].instructions


class GradingSession:
    def __init__(self, exercise):
        self.exercise = exercise
        self.commits = 0

    def get(self, model, ident):
        return self.exercise

    def commit(self):
        self.commits += 1


def make_attempt():
    return SimpleNamespace(
        id=uuid.uuid4(), user_id=uuid.uuid4(), exercise_id=uuid.uuid4(), response_text="Hallo Anna, ich komme spät.",
        status=AttemptStatus.GRADING, score=None, rubric_scores=None, feedback=None,
    )


def test_grade_attempt_sums_rubric_and_stores_feedback(monkeypatch):
    monkeypatch.setattr(schreiben_service.vocabulary_repo, "list_weak_words", lambda db, user_id: [])
    exercise = SimpleNamespace(teil=1, content={**TASK, "word_range": [20, 30], "max_score": 10})
    attempt = make_attempt()
    model, _ = scripted(grade(points=(2, 1, 2), communication=2, accuracy=1))

    schreiben_service.grade_attempt(GradingSession(exercise), model, attempt)

    assert attempt.status == AttemptStatus.GRADED
    assert attempt.score == 8
    assert [p["score"] for p in attempt.rubric_scores["content_points"]] == [2, 1, 2]
    assert attempt.feedback["word_count"] == 5
    assert attempt.feedback["corrections"][0]["corrected"] == "ich komme zu spät"


def test_failed_grading_marks_attempt_failed(monkeypatch):
    attempt = make_attempt()
    db = GradingSession(attempt)

    def boom(*a, **k):
        raise AIRunError("model unavailable")

    monkeypatch.setattr(schreiben_service, "grade_attempt", boom)
    monkeypatch.setattr(schreiben_service.agent_models, "get_model", lambda: None)
    job = SimpleNamespace(input={"attempt_id": str(attempt.id)})

    with pytest.raises(JobFailed) as exc:
        schreiben_service._grading_job(db, job)
    assert exc.value.code == "ai_failed"
    assert attempt.status == AttemptStatus.FAILED
    assert attempt.feedback == {"error": "model unavailable"}
    assert db.commits == 1
