import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.reading import (
    ReadingAttemptResult,
    ReadingAttemptSubmit,
    ReadingExerciseDetail,
    ReadingExerciseGenerateRequest,
    ReadingExerciseSummary,
)
from app.schemas.job import JobRead
from app.services import reading_service, scoring_service

router = APIRouter(prefix="/reading", tags=["reading"])


@router.get("/exercises", response_model=list[ReadingExerciseSummary])
def list_exercises(
    teil: int | None = None, db: Session = Depends(get_db)
) -> list[ReadingExerciseSummary]:
    exercises = reading_service.list_exercises(db, teil)
    return [ReadingExerciseSummary.model_validate(e) for e in exercises]


@router.get("/exercises/{exercise_id}", response_model=ReadingExerciseDetail)
def get_exercise(exercise_id: uuid.UUID, db: Session = Depends(get_db)) -> ReadingExerciseDetail:
    exercise = reading_service.get_exercise_or_404(db, exercise_id)
    return ReadingExerciseDetail.model_validate(exercise)


@router.post("/exercises/generate", response_model=JobRead, status_code=202)
def generate_exercise(
    payload: ReadingExerciseGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobRead:
    """Starts generation in the background. Poll GET /jobs/{id}; on success its result
    holds {"exercise_id": ...}."""
    job = reading_service.start_generation(db, current_user.id, payload)
    return JobRead.model_validate(job)


@router.post("/attempts", response_model=ReadingAttemptResult)
def submit_attempt(
    payload: ReadingAttemptSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReadingAttemptResult:
    exercise = reading_service.get_exercise_or_404(db, payload.exercise_id)
    attempt = scoring_service.score_attempt(db, current_user, exercise, payload.answers)
    correct_answers = exercise.answer_key.get("answers", {})
    explanations = exercise.answer_key.get("explanations", {})
    return ReadingAttemptResult(
        id=attempt.id,
        exercise_id=exercise.id,
        score=attempt.score,
        max_score=attempt.max_score,
        is_correct_per_question=attempt.is_correct_per_question,
        correct_answers=correct_answers,
        explanations=explanations,
    )
