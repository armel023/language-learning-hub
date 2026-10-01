import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.vocabulary import (
    VocabularyItemCreate,
    VocabularyItemRead,
    VocabularyItemUpdate,
    VocabularyListResponse,
)
from app.services import flashcard_service

router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])


@router.get("", response_model=VocabularyListResponse)
def list_vocabulary(
    deck_id: uuid.UUID | None = None,
    tag: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VocabularyListResponse:
    items, total = flashcard_service.list_vocabulary(
        db, current_user.id, deck_id, tag, search, page, page_size
    )
    return VocabularyListResponse(
        items=[VocabularyItemRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=VocabularyItemRead, status_code=201)
def create_vocabulary(
    payload: VocabularyItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VocabularyItemRead:
    item = flashcard_service.create_vocabulary(db, current_user.id, payload)
    return VocabularyItemRead.model_validate(item)


@router.get("/{item_id}", response_model=VocabularyItemRead)
def get_vocabulary(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VocabularyItemRead:
    item = flashcard_service.get_vocabulary_or_404(db, current_user.id, item_id)
    return VocabularyItemRead.model_validate(item)


@router.patch("/{item_id}", response_model=VocabularyItemRead)
def update_vocabulary(
    item_id: uuid.UUID,
    payload: VocabularyItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VocabularyItemRead:
    item = flashcard_service.update_vocabulary(db, current_user.id, item_id, payload)
    return VocabularyItemRead.model_validate(item)


@router.delete("/{item_id}", status_code=204)
def delete_vocabulary(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    flashcard_service.delete_vocabulary(db, current_user.id, item_id)
