import uuid

from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.live import sprechen as live
from app.models import DEFAULT_USER_ID, User
from app.schemas.job import JobRead
from app.schemas.reading import ReadingExerciseDetail as ExerciseDetail
from app.schemas.reading import ReadingExerciseSummary as ExerciseSummary
from app.schemas.sprechen import SprechenAttemptRead, SprechenGenerateRequest
from app.services import sprechen_service

# The exercise list/detail shapes are skill-agnostic; their Reading* names predate Sprechen.
router = APIRouter(prefix="/sprechen", tags=["sprechen"])


@router.get("/exercises", response_model=list[ExerciseSummary])
def list_exercises(teil: int | None = None, db: Session = Depends(get_db)) -> list[ExerciseSummary]:
    return [ExerciseSummary.model_validate(e) for e in sprechen_service.list_exercises(db, teil)]


@router.get("/exercises/{exercise_id}", response_model=ExerciseDetail)
def get_exercise(exercise_id: uuid.UUID, db: Session = Depends(get_db)) -> ExerciseDetail:
    """The candidate's card only; the partner's card stays on the server."""
    return ExerciseDetail.model_validate(sprechen_service.get_exercise_or_404(db, exercise_id))


@router.post("/exercises/generate", response_model=JobRead, status_code=202)
def generate_exercise(
    payload: SprechenGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobRead:
    return JobRead.model_validate(sprechen_service.start_generation(db, current_user.id, payload))


@router.get("/attempts/{attempt_id}", response_model=SprechenAttemptRead)
def get_attempt(
    attempt_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SprechenAttemptRead:
    return SprechenAttemptRead.model_validate(sprechen_service.get_attempt_or_404(db, current_user.id, attempt_id))


@router.websocket("/live/{exercise_id}")
async def live_session(websocket: WebSocket, exercise_id: uuid.UUID) -> None:
    """The live conversation with the AI partner. See app.live.sprechen for the protocol."""
    await websocket.accept()
    # Single-user app: the same placeholder identity as get_current_user.
    await live.run_session(websocket, exercise_id, DEFAULT_USER_ID)
