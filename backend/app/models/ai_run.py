import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import pg_enum


class AIRunStatus(str, enum.Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BUDGET_EXCEEDED = "budget_exceeded"


class AIRun(Base):
    """One agent run: what it was for, which model ran it, and the tokens it used.

    This is the app's own source of truth for token budgets and usage views; the OTel trace
    (linked by trace_id) holds the full prompt/response detail for debugging.
    """

    __tablename__ = "ai_runs"
    __table_args__ = (Index("ix_ai_runs_user_created", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # e.g. "lesen_teil1", "vocab_extraction"; later "schreiben_grading", "sprechen_session", ...
    feature: Mapped[str] = mapped_column(String(100))
    provider: Mapped[str] = mapped_column(String(50))
    model_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[AIRunStatus] = mapped_column(pg_enum(AIRunStatus, "ai_run_status"))

    requests: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
