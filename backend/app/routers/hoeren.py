import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.hoeren import HoerenAttemptResult, HoerenGenerateRequest
from app.schemas.job import JobRead
from app.schemas.reading import ReadingAttemptSubmit
from app.schemas.reading import ReadingExerciseDetail as ExerciseDetail
from app.schemas.reading import ReadingExerciseSummary as ExerciseSummary
from app.services import hoeren_service

# The exercise list/detail shapes are skill-agnostic; their Reading* names predate Hören.
router = APIRouter(prefix="/hoeren", tags=["hoeren"])


@router.get("/exercises", response_model=list[ExerciseSummary])
def list_exercises(teil: int | None = None, db: Session = Depends(get_db)) -> list[ExerciseSummary]:
    return [ExerciseSummary.model_validate(e) for e in hoeren_service.list_exercises(db, teil)]


@router.get("/exercises/{exercise_id}", response_model=ExerciseDetail)
def get_exercise(exercise_id: uuid.UUID, db: Session = Depends(get_db)) -> ExerciseDetail:
    return ExerciseDetail.model_validate(hoeren_service.get_exercise_or_404(db, exercise_id))


@router.post("/exercises/generate", response_model=JobRead, status_code=202)
def generate_exercise(
    payload: HoerenGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobRead:
    """Writes and checks the script, then synthesizes the audio. Poll GET /jobs/{id}."""
    return JobRead.model_validate(hoeren_service.start_generation(db, current_user.id, payload))


@router.post("/attempts", response_model=HoerenAttemptResult)
def submit_attempt(
    payload: ReadingAttemptSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HoerenAttemptResult:
    return hoeren_service.submit_attempt(db, current_user, payload)
