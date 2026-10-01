from sqlalchemy.orm import Session

from app.models import DEFAULT_USER_ID, User


def ensure_default_user(db: Session) -> None:
    existing = db.get(User, DEFAULT_USER_ID)
    if existing is not None:
        return
    db.add(User(id=DEFAULT_USER_ID, display_name="Default User"))
    db.commit()
