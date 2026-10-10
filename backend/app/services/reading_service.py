import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.agents.core import models as agent_models
from app.agents.core.models import ModelHandle
from app.agents.core.runner import AIBudgetExceeded, AIRunError
from app.agents.lesen.flow import RunContext, UnverifiedExercise, generate_checked
from app.agents.lesen.specs import SPECS
from app.config import get_settings
from app.jobs.runner import JobFailed, enqueue, job_handler
from app.models import Exercise, GeneratedBy, Job, Skill
from app.repositories import exercise_repo
from app.schemas.reading import ReadingExerciseGenerateRequest

GENERATE_JOB = "lesen_generate"


def list_exercises(db: Session, teil: int | None) -> list[Exercise]:
    return exercise_repo.list_exercises(db, Skill.LESEN, teil)


def get_exercise_or_404(db: Session, exercise_id: uuid.UUID) -> Exercise:
    exercise = exercise_repo.get_exercise(db, exercise_id)
    if exercise is None or exercise.skill != Skill.LESEN:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading exercise not found")
    return exercise


def start_generation(db: Session, user_id: uuid.UUID, payload: ReadingExerciseGenerateRequest) -> Job:
    """Queue exercise generation; the job's result is {"exercise_id": ...} once it succeeds."""
    return enqueue(db, GENERATE_JOB, user_id=user_id, input=payload.model_dump())


@job_handler(GENERATE_JOB)
def _generation_job(db: Session, job: Job) -> dict:
    payload = ReadingExerciseGenerateRequest.model_validate(job.input)
    try:
        exercise = generate_exercise(db, agent_models.get_model(), job.user_id, payload)
    except AIBudgetExceeded as exc:
        raise JobFailed("budget_exceeded", str(exc)) from exc
    except UnverifiedExercise as exc:
        raise JobFailed(
            "unverified",
            "The AI could not produce an exercise whose answers an independent check agreed with. "
            "Please try again.",
        ) from exc
    except AIRunError as exc:
        raise JobFailed("ai_failed", f"AI generation failed: {exc}") from exc
    return {"exercise_id": str(exercise.id)}


def generate_exercise(
    db: Session, model: ModelHandle, user_id: uuid.UUID | None, payload: ReadingExerciseGenerateRequest
) -> Exercise:
    settings = get_settings()
    spec = SPECS[payload.teil]
    result = generate_checked(
        RunContext(db, model, user_id, settings.ai_json_max_retries),
        spec,
        payload.topic,
        payload.level,
        max_revisions=settings.lesen_max_revisions,
        require_verification=settings.lesen_require_verification,
    )
    exercise = Exercise(
        skill=Skill.LESEN,
        teil=payload.teil,
        title=spec.title(result.output, payload.topic),
        level=payload.level,
        topic=payload.topic,
        content=result.content,
        answer_key=result.answer_key,
        generated_by=_generated_by(model),
        generation_prompt=spec.build_prompt(payload.topic, payload.level),
        generation_meta=result.meta(),
        user_id=user_id,
    )
    return exercise_repo.create_exercise(db, exercise)


def _generated_by(model: ModelHandle) -> GeneratedBy:
    return GeneratedBy.AI_OLLAMA if model.provider == "ollama" else GeneratedBy.AI_GEMINI
