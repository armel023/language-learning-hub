from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import DEFAULT_USER_ID, User


def get_current_user(db: Session = Depends(get_db)) -> Generator[User, None, None]:
    """Single-user placeholder. Swap this for real auth later without touching callers."""
    user = db.get(User, DEFAULT_USER_ID)
    if user is None:
        user = User(id=DEFAULT_USER_ID, display_name="Default User")
        db.add(user)
        db.commit()
        db.refresh(user)
    yield user
