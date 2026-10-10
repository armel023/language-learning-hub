import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.job import JobRead
from app.schemas.reading import ReadingExerciseDetail as ExerciseDetail
from app.schemas.reading import ReadingExerciseSummary as ExerciseSummary
from app.schemas.schreiben import SchreibenAttemptRead, SchreibenAttemptSubmit, SchreibenGenerateRequest
from app.services import schreiben_service

# The exercise list/detail shapes are skill-agnostic; their Reading* names predate Schreiben.
router = APIRouter(prefix="/schreiben", tags=["schreiben"])


@router.get("/exercises", response_model=list[ExerciseSummary])
def list_exercises(teil: int | None = None, db: Session = Depends(get_db)) -> list[ExerciseSummary]:
    return [ExerciseSummary.model_validate(e) for e in schreiben_service.list_exercises(db, teil)]


@router.get("/exercises/{exercise_id}", response_model=ExerciseDetail)
def get_exercise(exercise_id: uuid.UUID, db: Session = Depends(get_db)) -> ExerciseDetail:
    return ExerciseDetail.model_validate(schreiben_service.get_exercise_or_404(db, exercise_id))


@router.post("/exercises/generate", response_model=JobRead, status_code=202)
def generate_exercise(
    payload: SchreibenGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobRead:
    """Poll GET /jobs/{id}; on success its result holds {"exercise_id": ...}."""
    return JobRead.model_validate(schreiben_service.start_generation(db, current_user.id, payload))


@router.post("/attempts", response_model=SchreibenAttemptRead, status_code=202)
def submit_attempt(
    payload: SchreibenAttemptSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SchreibenAttemptRead:
    """Grading runs in the background; poll GET /schreiben/attempts/{id} until it is graded."""
    return SchreibenAttemptRead.model_validate(schreiben_service.submit_attempt(db, current_user, payload))


@router.get("/attempts/{attempt_id}", response_model=SchreibenAttemptRead)
def get_attempt(
    attempt_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SchreibenAttemptRead:
    attempt = schreiben_service.get_attempt_or_404(db, current_user.id, attempt_id)
    return SchreibenAttemptRead.model_validate(attempt)
