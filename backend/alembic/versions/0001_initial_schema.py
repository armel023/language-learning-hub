"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "decks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
    )

    op.create_table(
        "vocabulary_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("deck_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("decks.id"), nullable=True),
        sa.Column("word", sa.String(255), nullable=False),
        sa.Column(
            "part_of_speech",
            sa.Enum("noun", "verb", "adjective", "adverb", "phrase", "other", name="part_of_speech"),
            nullable=False,
        ),
        sa.Column("article", sa.Enum("der", "die", "das", name="article"), nullable=True),
        sa.Column("plural_form", sa.String(255), nullable=True),
        sa.Column("translation", sa.String(500), nullable=False),
        sa.Column("example_sentence_de", sa.Text(), nullable=True),
        sa.Column("example_sentence_translation", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "source",
            sa.Enum("manual", "ai_extracted", name="vocab_source"),
            nullable=False,
            server_default="manual",
        ),
        sa.Column("source_file_name", sa.String(500), nullable=True),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_due_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ease_factor", sa.Float(), nullable=False, server_default="2.5"),
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "vocabulary_tags",
        sa.Column(
            "vocabulary_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vocabulary_items.id"),
            primary_key=True,
        ),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tags.id"), primary_key=True),
    )

    op.create_table(
        "vocab_extraction_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("file_type", sa.Enum("pdf", "docx", "txt", name="vocab_file_type"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "processing", "completed", "failed", name="extraction_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("raw_ai_output", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "reading_exercises",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "exercise_type",
            sa.Enum("lesen_teil1", "lesen_teil2", "lesen_teil3", "lesen_teil4", name="exercise_type"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("level", sa.String(10), nullable=False, server_default="A2"),
        sa.Column("topic", sa.String(255), nullable=True),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("answer_key", postgresql.JSONB(), nullable=False),
        sa.Column(
            "generated_by",
            sa.Enum("ai_gemini", "ai_ollama", "manual", name="generated_by"),
            nullable=False,
        ),
        sa.Column("generation_prompt", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "reading_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "reading_exercise_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reading_exercises.id"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_score", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("answers", postgresql.JSONB(), nullable=False),
        sa.Column("is_correct_per_question", postgresql.JSONB(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("reading_attempts")
    op.drop_table("reading_exercises")
    op.drop_table("vocab_extraction_jobs")
    op.drop_table("vocabulary_tags")
    op.drop_table("vocabulary_items")
    op.drop_table("tags")
    op.drop_table("decks")
    op.drop_table("users")

    bind = op.get_bind()
    for enum_name in (
        "part_of_speech",
        "article",
        "vocab_source",
        "vocab_file_type",
        "extraction_status",
        "exercise_type",
        "generated_by",
    ):
        postgresql.ENUM(name=enum_name).drop(bind, checkfirst=True)
