import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import AttemptStatus

# --- AI outputs --------------------------------------------------------------------------


class SchreibenTaskAI(BaseModel):
    """A writing task as the generator produces it. Shown to the student as-is (no answer key)."""

    title: str = Field(description="Short German title, e.g. 'Verspätung zum Kurs'")
    situation: str = Field(description="1-3 simple German sentences setting the scene, addressed to the student (Sie).")
    recipient: str = Field(description="Who the message is for, e.g. 'Ihre Freundin Anna' or 'Ihre Kursleiterin Frau Weber'")
    formality: Literal["informal", "formal"]
    content_points: list[str] = Field(description="The points the student must write about, in German, as short phrases.")


class ContentPointGrade(BaseModel):
    point_number: int = Field(description="1-based, matching the task's content points in order.")
    score: int = Field(ge=0, le=2, description="0 = missing, 1 = partly or hard to understand, 2 = fully addressed.")
    comment: str = Field(description="One short sentence in English.")


class CriterionGrade(BaseModel):
    score: int = Field(ge=0, le=2)
    comment: str = Field(description="One or two short sentences in English.")


class Correction(BaseModel):
    original: str = Field(description="The student's exact words.")
    corrected: str
    explanation: str = Field(description="Short, simple English explanation of the rule.")


class SchreibenGradeAI(BaseModel):
    content_points: list[ContentPointGrade]
    communication: CriterionGrade = Field(description="Greeting/closing, register (du/Sie), coherence, fits the recipient.")
    accuracy: CriterionGrade = Field(description="Grammar, spelling and word choice, judged by whether errors hinder understanding.")
    corrections: list[Correction] = Field(default_factory=list, description="The most useful corrections, at most 6.")
    summary: str = Field(description="2-3 encouraging, concrete sentences in English.")
    improved_version: str = Field(description="The student's text rewritten as a strong A2 answer, keeping their ideas.")


# --- API ---------------------------------------------------------------------------------


class SchreibenGenerateRequest(BaseModel):
    teil: Literal[1, 2]
    topic: str | None = None
    level: str = "A2"


class SchreibenAttemptSubmit(BaseModel):
    exercise_id: uuid.UUID
    response_text: str = Field(min_length=1, max_length=5000)


class SchreibenAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    exercise_id: uuid.UUID
    status: AttemptStatus
    response_text: str | None
    score: int | None
    max_score: int
    rubric_scores: dict | None
    feedback: dict | None
    submitted_at: datetime | None
