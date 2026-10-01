import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import VocabSource, VocabularyItem
from app.repositories import vocabulary_repo
from app.schemas.vocabulary import VocabularyItemCreate, VocabularyItemUpdate


def list_vocabulary(
    db: Session,
    user_id: uuid.UUID,
    deck_id: uuid.UUID | None,
    tag: str | None,
    search: str | None,
    page: int,
    page_size: int,
) -> tuple[list[VocabularyItem], int]:
    return vocabulary_repo.list_vocabulary(db, user_id, deck_id, tag, search, page, page_size)


def get_vocabulary_or_404(db: Session, user_id: uuid.UUID, item_id: uuid.UUID) -> VocabularyItem:
    item = vocabulary_repo.get_vocabulary(db, user_id, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vocabulary item not found")
    return item


def create_vocabulary(
    db: Session, user_id: uuid.UUID, payload: VocabularyItemCreate
) -> VocabularyItem:
    item = VocabularyItem(
        user_id=user_id,
        source=VocabSource.MANUAL,
        **payload.model_dump(),
    )
    return vocabulary_repo.create_vocabulary(db, item)


def update_vocabulary(
    db: Session, user_id: uuid.UUID, item_id: uuid.UUID, payload: VocabularyItemUpdate
) -> VocabularyItem:
    item = get_vocabulary_or_404(db, user_id, item_id)
    fields = payload.model_dump(exclude_unset=True)
    return vocabulary_repo.update_vocabulary(db, item, fields)


def delete_vocabulary(db: Session, user_id: uuid.UUID, item_id: uuid.UUID) -> None:
    item = get_vocabulary_or_404(db, user_id, item_id)
    vocabulary_repo.delete_vocabulary(db, item)
