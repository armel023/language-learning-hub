import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import pg_enum


class Skill(str, enum.Enum):
    LESEN = "lesen"
    HOEREN = "hoeren"
    SCHREIBEN = "schreiben"
    SPRECHEN = "sprechen"


# Number of Teile per skill in the Goethe-Zertifikat A2.
TEILE_PER_SKILL = {Skill.LESEN: 4, Skill.HOEREN: 4, Skill.SCHREIBEN: 2, Skill.SPRECHEN: 3}


class GeneratedBy(str, enum.Enum):
    AI_GEMINI = "ai_gemini"
    AI_OLLAMA = "ai_ollama"
    MANUAL = "manual"


class Exercise(Base):
    """One exam-style task for any skill. The shape of `content` (and `answer_key`/`media`)
    depends on skill + teil; the matching Pydantic schemas live in app.schemas."""

    __tablename__ = "exercises"
    __table_args__ = (
        CheckConstraint("teil BETWEEN 1 AND 4", name="ck_exercises_teil"),
        Index("ix_exercises_skill_teil_created", "skill", "teil", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill: Mapped[Skill] = mapped_column(pg_enum(Skill, "skill"))
    teil: Mapped[int] = mapped_column(SmallInteger)
    title: Mapped[str] = mapped_column(String(255))
    level: Mapped[str] = mapped_column(String(10), default="A2")
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)

    content: Mapped[dict] = mapped_column(JSONB)
    # Objective answers (Lesen/Hören). NULL for Schreiben/Sprechen, which are graded by rubric.
    answer_key: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Generated assets, e.g. Hören audio: {"audio": [{"segment": 1, "url": "...", "duration_s": 12.3}]}
    media: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    generated_by: Mapped[GeneratedBy] = mapped_column(pg_enum(GeneratedBy, "generated_by"))
    generation_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    # How the exercise was produced, e.g. {"verified": true, "rounds": [{"round": 0, "problems": []}]}
    generation_meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Who generated it. Exercises are shared practice material, so this is attribution, not access.
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def exercise_type(self) -> str:
        """e.g. "lesen_teil1". Kept for API compatibility with the original Lesen-only schema."""
        return f"{self.skill.value}_teil{self.teil}"
