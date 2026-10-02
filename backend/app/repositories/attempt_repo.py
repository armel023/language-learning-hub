from sqlalchemy.orm import Session

from app.models import ReadingAttempt


def create_attempt(db: Session, attempt: ReadingAttempt) -> ReadingAttempt:
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt
