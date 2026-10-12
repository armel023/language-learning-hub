import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import pg_enum


class AttemptStatus(str, enum.Enum):
    # Lesen/Hören are scored instantly on submit; Schreiben/Sprechen go submitted -> grading -> graded.
    SUBMITTED = "submitted"
    GRADING = "grading"
    GRADED = "graded"
    FAILED = "failed"


class Attempt(Base):
    """A user's answer to one Exercise. Which response fields are set depends on the skill:
    answers (Lesen/Hören choices), response_text (Schreiben), audio_url + transcript (Sprechen)."""

    __tablename__ = "attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    exercise_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("exercises.id"), nullable=False)

    status: Mapped[AttemptStatus] = mapped_column(
        pg_enum(AttemptStatus, "attempt_status"), default=AttemptStatus.GRADED
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # NULL until graded (immediately for objective skills, after AI grading for the others).
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_score: Mapped[int] = mapped_column(Integer, default=5)

    answers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_correct_per_question: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # Sprechen turns: [{"role": "examiner"|"candidate", "text": "...", "start_s": 0.0}, ...]
    transcript: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Per-criterion points, e.g. Schreiben {"aufgabenerfuellung": 3, "kohaerenz": 2, ...}
    rubric_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Structured AI feedback: {"summary": "...", "corrections": [...], "weak_words": [...]}
    feedback: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
