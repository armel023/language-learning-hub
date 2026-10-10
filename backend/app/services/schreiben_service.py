import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.agents import schreiben
from app.agents.core import models as agent_models
from app.agents.core.models import ModelHandle
from app.agents.core.runner import AIBudgetExceeded, AIRunError, run_agent
from app.config import get_settings
from app.jobs.runner import JobFailed, enqueue, job_handler
from app.models import Attempt, AttemptStatus, Exercise, GeneratedBy, Job, Skill, User
from app.repositories import attempt_repo, exercise_repo, vocabulary_repo
from app.schemas.schreiben import (
    SchreibenAttemptSubmit,
    SchreibenGenerateRequest,
    SchreibenGradeAI,
    SchreibenTaskAI,
)

GENERATE_JOB = "schreiben_generate"
GRADE_JOB = "schreiben_grade"


def list_exercises(db: Session, teil: int | None) -> list[Exercise]:
    return exercise_repo.list_exercises(db, Skill.SCHREIBEN, teil)


def get_exercise_or_404(db: Session, exercise_id: uuid.UUID) -> Exercise:
    exercise = exercise_repo.get_exercise(db, exercise_id)
    if exercise is None or exercise.skill != Skill.SCHREIBEN:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schreiben exercise not found")
    return exercise


def get_attempt_or_404(db: Session, user_id: uuid.UUID, attempt_id: uuid.UUID) -> Attempt:
    attempt = db.get(Attempt, attempt_id)
    if attempt is None or attempt.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    return attempt


# --- task generation ---------------------------------------------------------------------


def start_generation(db: Session, user_id: uuid.UUID, payload: SchreibenGenerateRequest) -> Job:
    return enqueue(db, GENERATE_JOB, user_id=user_id, input=payload.model_dump())


@job_handler(GENERATE_JOB)
def _generation_job(db: Session, job: Job) -> dict:
    payload = SchreibenGenerateRequest.model_validate(job.input)
    try:
        exercise = generate_exercise(db, agent_models.get_model(), job.user_id, payload)
    except AIBudgetExceeded as exc:
        raise JobFailed("budget_exceeded", str(exc)) from exc
    except AIRunError as exc:
        raise JobFailed("ai_failed", f"AI generation failed: {exc}") from exc
    return {"exercise_id": str(exercise.id)}


def generate_exercise(
    db: Session, model: ModelHandle, user_id: uuid.UUID | None, payload: SchreibenGenerateRequest
) -> Exercise:
    spec = schreiben.SPECS[payload.teil]
    prompt = schreiben.build_generator_prompt(spec, payload.topic, payload.level)
    task: SchreibenTaskAI = run_agent(
        db, schreiben.generator_agent, prompt, feature=f"schreiben_teil{spec.teil}",
        model=model, user_id=user_id, max_retries=get_settings().ai_json_max_retries, deps=spec,
    )
    exercise = Exercise(
        skill=Skill.SCHREIBEN,
        teil=spec.teil,
        title=task.title,
        level=payload.level,
        topic=payload.topic,
        content={**task.model_dump(), "word_range": list(spec.word_range), "max_score": schreiben.max_score(spec)},
        answer_key=None,
        generated_by=GeneratedBy.AI_OLLAMA if model.provider == "ollama" else GeneratedBy.AI_GEMINI,
        generation_prompt=prompt,
        user_id=user_id,
    )
    return exercise_repo.create_exercise(db, exercise)


# --- grading -----------------------------------------------------------------------------


def submit_attempt(db: Session, user: User, payload: SchreibenAttemptSubmit) -> Attempt:
    """Store the answer and queue AI grading; the attempt moves grading -> graded (or failed)."""
    exercise = get_exercise_or_404(db, payload.exercise_id)
    attempt = attempt_repo.create_attempt(
        db,
        Attempt(
            user_id=user.id,
            exercise_id=exercise.id,
            status=AttemptStatus.GRADING,
            submitted_at=datetime.now(timezone.utc),
            response_text=payload.response_text.strip(),
            max_score=schreiben.max_score(schreiben.SPECS[exercise.teil]),
        ),
    )
    enqueue(db, GRADE_JOB, user_id=user.id, input={"attempt_id": str(attempt.id)})
    db.refresh(attempt)
    return attempt


@job_handler(GRADE_JOB)
def _grading_job(db: Session, job: Job) -> dict:
    attempt = db.get(Attempt, uuid.UUID(job.input["attempt_id"]))
    try:
        grade_attempt(db, agent_models.get_model(), attempt)
    except (AIBudgetExceeded, AIRunError) as exc:
        attempt.status = AttemptStatus.FAILED
        attempt.feedback = {"error": str(exc)}
        db.commit()  # persisted before raising: the runner rolls back on failure
        code = "budget_exceeded" if isinstance(exc, AIBudgetExceeded) else "ai_failed"
        raise JobFailed(code, f"Grading failed: {exc}") from exc
    return {"attempt_id": str(attempt.id), "score": attempt.score}


def grade_attempt(db: Session, model: ModelHandle, attempt: Attempt) -> Attempt:
    exercise = db.get(Exercise, attempt.exercise_id)
    spec = schreiben.SPECS[exercise.teil]
    deps = schreiben.GradingDeps(
        task=SchreibenTaskAI.model_validate(exercise.content),
        spec=spec,
        word_count=schreiben.count_words(attempt.response_text),
        weak_words=vocabulary_repo.list_weak_words(db, attempt.user_id),
    )
    grade: SchreibenGradeAI = run_agent(
        db, schreiben.grader_agent, schreiben.build_grader_prompt(attempt.response_text),
        feature=f"schreiben_teil{spec.teil}_grade", model=model, user_id=attempt.user_id,
        max_retries=get_settings().ai_json_max_retries, deps=deps,
    )
    attempt.score = sum(p.score for p in grade.content_points) + grade.communication.score + grade.accuracy.score
    attempt.rubric_scores = {
        "content_points": [p.model_dump() for p in grade.content_points],
        "communication": grade.communication.model_dump(),
        "accuracy": grade.accuracy.model_dump(),
    }
    attempt.feedback = {
        "summary": grade.summary,
        "corrections": [c.model_dump() for c in grade.corrections],
        "improved_version": grade.improved_version,
        "word_count": deps.word_count,
        "word_range": list(spec.word_range),
    }
    attempt.status = AttemptStatus.GRADED
    db.commit()
    return attempt
