import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.reading_exercise import ExerciseType


class ReadingExerciseSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    exercise_type: ExerciseType
    title: str
    level: str
    topic: str | None
    created_at: datetime


class ReadingExerciseDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    exercise_type: ExerciseType
    title: str
    level: str
    topic: str | None
    content: dict
    created_at: datetime


class ReadingExerciseGenerateRequest(BaseModel):
    teil: Literal[1, 2, 3, 4]
    topic: str | None = None
    level: str = "A2"


class ReadingAttemptSubmit(BaseModel):
    exercise_id: uuid.UUID
    # int option index for Teil 1-3, ad-code/"X" string for Teil 4
    answers: dict[str, int | str]


class ReadingAttemptResult(BaseModel):
    id: uuid.UUID
    exercise_id: uuid.UUID
    score: int
    max_score: int
    is_correct_per_question: dict[str, bool]
    correct_answers: dict[str, int | str]
    explanations: dict[str, str]
