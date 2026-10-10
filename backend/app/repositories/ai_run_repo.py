import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AIRun


def tokens_used_today(db: Session, user_id: uuid.UUID | None) -> int:
    """Total tokens this user has spent since 00:00 UTC, including failed runs."""
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    stmt = select(func.coalesce(func.sum(AIRun.total_tokens), 0)).where(AIRun.created_at >= start_of_day)
    stmt = stmt.where(AIRun.user_id.is_(None) if user_id is None else AIRun.user_id == user_id)
    return int(db.scalar(stmt) or 0)


def create_run(db: Session, run: AIRun) -> AIRun:
    db.add(run)
    db.commit()
    return run
