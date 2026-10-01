import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Deck


def list_decks(db: Session, user_id: uuid.UUID) -> list[Deck]:
    stmt = select(Deck).where(Deck.user_id == user_id).order_by(Deck.created_at.desc())
    return list(db.scalars(stmt).all())


def get_deck(db: Session, user_id: uuid.UUID, deck_id: uuid.UUID) -> Deck | None:
    stmt = select(Deck).where(Deck.id == deck_id, Deck.user_id == user_id)
    return db.scalars(stmt).first()


def create_deck(db: Session, deck: Deck) -> Deck:
    db.add(deck)
    db.commit()
    db.refresh(deck)
    return deck


def update_deck(db: Session, deck: Deck, fields: dict) -> Deck:
    for key, value in fields.items():
        setattr(deck, key, value)
    db.commit()
    db.refresh(deck)
    return deck


def delete_deck(db: Session, deck: Deck) -> None:
    db.delete(deck)
    db.commit()
