from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.study import StudyReviewRequest, StudySessionStart
from app.schemas.vocabulary import VocabularyItemRead
from app.services import study_service

router = APIRouter(prefix="/study", tags=["study"])


@router.post("/sessions", response_model=StudySessionStart)
def start_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudySessionStart:
    session_number, words = study_service.start_session(db, current_user)
    return StudySessionStart(
        session_number=session_number,
        words=[VocabularyItemRead.model_validate(word) for word in words],
    )


@router.post("/reviews", response_model=VocabularyItemRead)
def record_review(
    payload: StudyReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VocabularyItemRead:
    item = study_service.record_review(db, current_user, payload.vocabulary_id, payload.outcome)
    return VocabularyItemRead.model_validate(item)
