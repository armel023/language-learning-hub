import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import pg_enum


class ExerciseType(str, enum.Enum):
    LESEN_TEIL1 = "lesen_teil1"
    LESEN_TEIL2 = "lesen_teil2"
    LESEN_TEIL3 = "lesen_teil3"
    LESEN_TEIL4 = "lesen_teil4"


class GeneratedBy(str, enum.Enum):
    AI_GEMINI = "ai_gemini"
    AI_OLLAMA = "ai_ollama"
    MANUAL = "manual"


class ReadingExercise(Base):
    __tablename__ = "reading_exercises"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exercise_type: Mapped[ExerciseType] = mapped_column(pg_enum(ExerciseType, "exercise_type"))
    title: Mapped[str] = mapped_column(String(255))
    level: Mapped[str] = mapped_column(String(10), default="A2")
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)

    content: Mapped[dict] = mapped_column(JSONB)
    answer_key: Mapped[dict] = mapped_column(JSONB)

    generated_by: Mapped[GeneratedBy] = mapped_column(pg_enum(GeneratedBy, "generated_by"))
    generation_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
