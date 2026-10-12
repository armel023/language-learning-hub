import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.agents import sprechen
from app.agents.core import models as agent_models
from app.agents.core.models import ModelHandle
from app.agents.core.runner import AIBudgetExceeded, AIRunError, run_agent
from app.config import get_settings
from app.jobs.runner import JobFailed, enqueue, job_handler
from app.models import Attempt, AttemptStatus, Exercise, GeneratedBy, Job, Skill
from app.repositories import attempt_repo, exercise_repo
from app.schemas.sprechen import SprechenGenerateRequest, SprechenGradeAI

GENERATE_JOB = "sprechen_generate"
GRADE_JOB = "sprechen_grade"


def list_exercises(db: Session, teil: int | None) -> list[Exercise]:
    return exercise_repo.list_exercises(db, Skill.SPRECHEN, teil)


def get_exercise_or_404(db: Session, exercise_id: uuid.UUID) -> Exercise:
    exercise = exercise_repo.get_exercise(db, exercise_id)
    if exercise is None or exercise.skill != Skill.SPRECHEN:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sprechen exercise not found")
    return exercise


def get_attempt_or_404(db: Session, user_id: uuid.UUID, attempt_id: uuid.UUID) -> Attempt:
    attempt = db.get(Attempt, attempt_id)
    if attempt is None or attempt.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    return attempt


# --- card generation -----------------------------------------------------------------------------


def start_generation(db: Session, user_id: uuid.UUID, payload: SprechenGenerateRequest) -> Job:
    return enqueue(db, GENERATE_JOB, user_id=user_id, input=payload.model_dump())


@job_handler(GENERATE_JOB)
def _generation_job(db: Session, job: Job) -> dict:
    payload = SprechenGenerateRequest.model_validate(job.input)
    try:
        exercise = generate_exercise(db, agent_models.get_model(), job.user_id, payload)
    except AIBudgetExceeded as exc:
        raise JobFailed("budget_exceeded", str(exc)) from exc
    except AIRunError as exc:
        raise JobFailed("ai_failed", f"AI generation failed: {exc}") from exc
    return {"exercise_id": str(exercise.id)}


def generate_exercise(
    db: Session, model: ModelHandle, user_id: uuid.UUID | None, payload: SprechenGenerateRequest
) -> Exercise:
    spec = sprechen.card_spec(payload.teil, payload.variant)
    prompt = sprechen.build_generator_prompt(payload.teil, payload.topic, payload.level)
    out = run_agent(
        db, spec.agent, prompt, feature=f"sprechen_teil{payload.teil}",
        model=model, user_id=user_id, max_retries=get_settings().ai_json_max_retries,
    )
    content, hidden = spec.split(out)
    exercise = Exercise(
        skill=Skill.SPRECHEN,
        teil=payload.teil,
        title=spec.title(out),
        level=payload.level,
        topic=payload.topic,
        content=content,
        # Not an answer key here: the partner's card, which the candidate must not see. The
        # exercise API never returns answer_key; only the live partner and the grader read it.
        answer_key=hidden,
        generated_by=GeneratedBy.AI_OLLAMA if model.provider == "ollama" else GeneratedBy.AI_GEMINI,
        generation_prompt=prompt,
        user_id=user_id,
    )
    return exercise_repo.create_exercise(db, exercise)


# --- after the live conversation -----------------------------------------------------------------


def save_session(db: Session, user_id: uuid.UUID, exercise_id: uuid.UUID, transcript: list[dict],
                 duration_s: float) -> Attempt:
    attempt = attempt_repo.create_attempt(db, Attempt(
        user_id=user_id,
        exercise_id=exercise_id,
        status=AttemptStatus.GRADING,
        submitted_at=datetime.now(timezone.utc),
        transcript=transcript,
        max_score=sprechen.MAX_SCORE,
        feedback={"duration_s": round(duration_s)},
    ))
    enqueue(db, GRADE_JOB, user_id=user_id, input={"attempt_id": str(attempt.id)})
    db.refresh(attempt)
    return attempt


@job_handler(GRADE_JOB)
def _grading_job(db: Session, job: Job) -> dict:
    attempt = db.get(Attempt, uuid.UUID(job.input["attempt_id"]))
    try:
        grade_attempt(db, agent_models.get_model(), attempt)
    except (AIBudgetExceeded, AIRunError) as exc:
        attempt.status = AttemptStatus.FAILED
        attempt.feedback = {**(attempt.feedback or {}), "error": str(exc)}
        db.commit()  # persisted before raising: the runner rolls back on failure
        code = "budget_exceeded" if isinstance(exc, AIBudgetExceeded) else "ai_failed"
        raise JobFailed(code, f"Feedback failed: {exc}") from exc
    return {"attempt_id": str(attempt.id), "score": attempt.score}


def grade_attempt(db: Session, model: ModelHandle, attempt: Attempt) -> Attempt:
    exercise = db.get(Exercise, attempt.exercise_id)
    hidden = exercise.answer_key or {}
    deps = sprechen.GradingDeps(
        teil=exercise.teil,
        content=exercise.content,
        hidden=hidden,
        checklist_items=sprechen.checklist_items(exercise.teil, exercise.content, hidden),
    )
    grade: SprechenGradeAI = run_agent(
        db, sprechen.grader_agent, f"Transcript:\n{sprechen.format_transcript(attempt.transcript)}",
        feature=f"sprechen_teil{exercise.teil}_grade", model=model, user_id=attempt.user_id,
        max_retries=get_settings().ai_json_max_retries, deps=deps,
    )
    attempt.score = sprechen.score(grade)
    attempt.rubric_scores = {
        "checklist": [i.model_dump() for i in grade.checklist],
        "task": attempt.score - grade.interaction.score - grade.accuracy.score,
        "task_max": sprechen.TASK_MAX,
        "interaction": grade.interaction.model_dump(),
        "accuracy": grade.accuracy.model_dump(),
    }
    attempt.feedback = {
        **(attempt.feedback or {}),
        "summary": grade.summary,
        "corrections": [c.model_dump() for c in grade.corrections],
        "better_phrases": grade.better_phrases,
    }
    attempt.status = AttemptStatus.GRADED
    db.commit()
    return attempt
