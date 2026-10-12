import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import pg_enum


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Job(Base):
    """A unit of background work (agent runs that are too slow to hold an HTTP request open).

    The client gets the job id back immediately and polls GET /jobs/{id}; `result` holds a
    small pointer to what was produced (e.g. {"exercise_id": "..."}), not the payload itself.
    """

    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_status", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Handler key, e.g. "lesen_generate", "vocab_extraction"; later "schreiben_grade", ...
    kind: Mapped[str] = mapped_column(String(100))
    status: Mapped[JobStatus] = mapped_column(pg_enum(JobStatus, "job_status"), default=JobStatus.PENDING)
    input: Mapped[dict] = mapped_column(JSONB, default=dict)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Machine-readable failure reason the UI can branch on ("budget_exceeded", "ai_failed", ...).
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
