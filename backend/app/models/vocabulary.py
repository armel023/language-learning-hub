import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import pg_enum


class PartOfSpeech(str, enum.Enum):
    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PHRASE = "phrase"
    OTHER = "other"


class Article(str, enum.Enum):
    DER = "der"
    DIE = "die"
    DAS = "das"


class VocabSource(str, enum.Enum):
    MANUAL = "manual"
    AI_EXTRACTED = "ai_extracted"


vocabulary_tags = Table(
    "vocabulary_tags",
    Base.metadata,
    Column("vocabulary_item_id", UUID(as_uuid=True), ForeignKey("vocabulary_items.id"), primary_key=True),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("tags.id"), primary_key=True),
)


class VocabularyItem(Base):
    __tablename__ = "vocabulary_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    deck_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("decks.id"), nullable=True)

    word: Mapped[str] = mapped_column(String(255))
    part_of_speech: Mapped[PartOfSpeech] = mapped_column(pg_enum(PartOfSpeech, "part_of_speech"))
    article: Mapped[Article | None] = mapped_column(pg_enum(Article, "article"), nullable=True)
    plural_form: Mapped[str | None] = mapped_column(String(255), nullable=True)
    translation: Mapped[str] = mapped_column(String(500))
    example_sentence_de: Mapped[str | None] = mapped_column(Text, nullable=True)
    example_sentence_translation: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[VocabSource] = mapped_column(pg_enum(VocabSource, "vocab_source"), default=VocabSource.MANUAL)
    source_file_name: Mapped[str | None] = mapped_column(String(500), nullable=True)

    review_count: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    incorrect_hard_count: Mapped[int] = mapped_column(Integer, default=0)
    incorrect_moderate_count: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # The study session number (User.study_session_count) at or after which this word becomes
    # eligible to be picked again. NULL means eligible immediately (never missed, or cleared
    # by a correct answer).
    study_due_at_session: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tags = relationship("Tag", secondary=vocabulary_tags)


class ExtractionStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileType(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class VocabExtractionJob(Base):
    __tablename__ = "vocab_extraction_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    original_filename: Mapped[str] = mapped_column(String(500))
    file_type: Mapped[FileType] = mapped_column(pg_enum(FileType, "vocab_file_type"))
    status: Mapped[ExtractionStatus] = mapped_column(
        pg_enum(ExtractionStatus, "extraction_status"), default=ExtractionStatus.PENDING
    )
    raw_ai_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
