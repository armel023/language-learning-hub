import uuid
from typing import Literal

from pydantic import BaseModel

from app.schemas.vocabulary import VocabularyItemRead

StudyOutcome = Literal["correct", "incorrect_hard", "incorrect_moderate"]


class StudySessionStart(BaseModel):
    session_number: int
    words: list[VocabularyItemRead]


class StudyReviewRequest(BaseModel):
    vocabulary_id: uuid.UUID
    outcome: StudyOutcome
