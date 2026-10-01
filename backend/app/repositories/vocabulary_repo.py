import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import VocabularyItem


def list_vocabulary(
    db: Session,
    user_id: uuid.UUID,
    deck_id: uuid.UUID | None = None,
    tag: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[VocabularyItem], int]:
    stmt = select(VocabularyItem).where(VocabularyItem.user_id == user_id)
    if deck_id is not None:
        stmt = stmt.where(VocabularyItem.deck_id == deck_id)
    if tag is not None:
        stmt = stmt.join(VocabularyItem.tags).where(VocabularyItem.tags.any(name=tag))
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(VocabularyItem.word.ilike(pattern), VocabularyItem.translation.ilike(pattern))
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    stmt = stmt.order_by(VocabularyItem.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = list(db.scalars(stmt).all())
    return items, total


def get_vocabulary(db: Session, user_id: uuid.UUID, item_id: uuid.UUID) -> VocabularyItem | None:
    stmt = select(VocabularyItem).where(
        VocabularyItem.id == item_id, VocabularyItem.user_id == user_id
    )
    return db.scalars(stmt).first()


def create_vocabulary(db: Session, item: VocabularyItem) -> VocabularyItem:
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_vocabulary(db: Session, item: VocabularyItem, fields: dict) -> VocabularyItem:
    for key, value in fields.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def delete_vocabulary(db: Session, item: VocabularyItem) -> None:
    db.delete(item)
    db.commit()


def list_due_vocabulary(db: Session, user_id: uuid.UUID, session_number: int) -> list[VocabularyItem]:
    """Words flagged incorrect_hard/incorrect_moderate whose wait period has elapsed."""
    stmt = select(VocabularyItem).where(
        VocabularyItem.user_id == user_id,
        VocabularyItem.study_due_at_session.is_not(None),
        VocabularyItem.study_due_at_session <= session_number,
    )
    return list(db.scalars(stmt).all())


def list_fillable_vocabulary(
    db: Session, user_id: uuid.UUID, exclude_ids: set[uuid.UUID]
) -> list[VocabularyItem]:
    """Words with no outstanding due date: never studied, or cleared by a correct answer."""
    stmt = select(VocabularyItem).where(
        VocabularyItem.user_id == user_id,
        VocabularyItem.study_due_at_session.is_(None),
    )
    if exclude_ids:
        stmt = stmt.where(VocabularyItem.id.notin_(exclude_ids))
    return list(db.scalars(stmt).all())
