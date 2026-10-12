from sqlalchemy.orm import Session

from app.models import Attempt


def create_attempt(db: Session, attempt: Attempt) -> Attempt:
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt
