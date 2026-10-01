import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.deck import DeckCreate, DeckRead, DeckUpdate
from app.services import deck_service

router = APIRouter(prefix="/decks", tags=["decks"])


@router.get("", response_model=list[DeckRead])
def list_decks(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[DeckRead]:
    decks = deck_service.list_decks(db, current_user.id)
    return [DeckRead.model_validate(deck) for deck in decks]


@router.post("", response_model=DeckRead, status_code=201)
def create_deck(
    payload: DeckCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeckRead:
    deck = deck_service.create_deck(db, current_user.id, payload)
    return DeckRead.model_validate(deck)


@router.patch("/{deck_id}", response_model=DeckRead)
def update_deck(
    deck_id: uuid.UUID,
    payload: DeckUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeckRead:
    deck = deck_service.update_deck(db, current_user.id, deck_id, payload)
    return DeckRead.model_validate(deck)


@router.delete("/{deck_id}", status_code=204)
def delete_deck(
    deck_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    deck_service.delete_deck(db, current_user.id, deck_id)
