import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Exercise, Skill


def list_exercises(db: Session, skill: Skill, teil: int | None = None) -> list[Exercise]:
    stmt = select(Exercise).where(Exercise.skill == skill)
    if teil is not None:
        stmt = stmt.where(Exercise.teil == teil)
    stmt = stmt.order_by(Exercise.created_at.desc())
    return list(db.scalars(stmt).all())


def get_exercise(db: Session, exercise_id: uuid.UUID) -> Exercise | None:
    return db.get(Exercise, exercise_id)


def create_exercise(db: Session, exercise: Exercise) -> Exercise:
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return exercise
