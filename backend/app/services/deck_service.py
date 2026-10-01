import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Deck
from app.repositories import deck_repo
from app.schemas.deck import DeckCreate, DeckUpdate


def list_decks(db: Session, user_id: uuid.UUID) -> list[Deck]:
    return deck_repo.list_decks(db, user_id)


def get_deck_or_404(db: Session, user_id: uuid.UUID, deck_id: uuid.UUID) -> Deck:
    deck = deck_repo.get_deck(db, user_id, deck_id)
    if deck is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    return deck


def create_deck(db: Session, user_id: uuid.UUID, payload: DeckCreate) -> Deck:
    deck = Deck(user_id=user_id, **payload.model_dump())
    return deck_repo.create_deck(db, deck)


def update_deck(db: Session, user_id: uuid.UUID, deck_id: uuid.UUID, payload: DeckUpdate) -> Deck:
    deck = get_deck_or_404(db, user_id, deck_id)
    fields = payload.model_dump(exclude_unset=True)
    return deck_repo.update_deck(db, deck, fields)


def delete_deck(db: Session, user_id: uuid.UUID, deck_id: uuid.UUID) -> None:
    deck = get_deck_or_404(db, user_id, deck_id)
    deck_repo.delete_deck(db, deck)
