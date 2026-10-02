import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ReadingExercise
from app.models.reading_exercise import ExerciseType


def list_exercises(db: Session, exercise_type: ExerciseType | None = None) -> list[ReadingExercise]:
    stmt = select(ReadingExercise)
    if exercise_type is not None:
        stmt = stmt.where(ReadingExercise.exercise_type == exercise_type)
    stmt = stmt.order_by(ReadingExercise.created_at.desc())
    return list(db.scalars(stmt).all())


def get_exercise(db: Session, exercise_id: uuid.UUID) -> ReadingExercise | None:
    return db.get(ReadingExercise, exercise_id)


def create_exercise(db: Session, exercise: ReadingExercise) -> ReadingExercise:
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return exercise
