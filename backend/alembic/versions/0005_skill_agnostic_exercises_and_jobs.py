"""skill-agnostic exercises/attempts + background jobs

reading_exercises -> exercises (skill + teil instead of the Lesen-only exercise_type enum),
reading_attempts -> attempts (free-text/audio/rubric fields for Schreiben/Sprechen),
and a generic jobs table for background agent runs. Existing Lesen data is converted in place.

Revision ID: 0005_skill_agnostic_exercises
Revises: 0004_ai_runs
Create Date: 2026-10-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005_skill_agnostic_exercises"
down_revision: Union[str, None] = "0004_ai_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

skill_enum = postgresql.ENUM("lesen", "hoeren", "schreiben", "sprechen", name="skill", create_type=False)
attempt_status_enum = postgresql.ENUM(
    "submitted", "grading", "graded", "failed", name="attempt_status", create_type=False
)
job_status_enum = postgresql.ENUM("pending", "running", "succeeded", "failed", name="job_status", create_type=False)
exercise_type_enum = postgresql.ENUM(
    "lesen_teil1", "lesen_teil2", "lesen_teil3", "lesen_teil4", name="exercise_type", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    skill_enum.create(bind)
    attempt_status_enum.create(bind)
    job_status_enum.create(bind)

    # --- exercises -----------------------------------------------------------------------
    op.rename_table("reading_exercises", "exercises")
    op.execute("ALTER INDEX reading_exercises_pkey RENAME TO exercises_pkey")

    op.add_column("exercises", sa.Column("skill", skill_enum, nullable=True))
    op.add_column("exercises", sa.Column("teil", sa.SmallInteger(), nullable=True))
    op.execute(
        "UPDATE exercises SET skill = split_part(exercise_type::text, '_teil', 1)::skill, "
        "teil = split_part(exercise_type::text, '_teil', 2)::smallint"
    )
    op.alter_column("exercises", "skill", nullable=False)
    op.alter_column("exercises", "teil", nullable=False)
    op.drop_column("exercises", "exercise_type")
    exercise_type_enum.drop(bind)

    op.alter_column("exercises", "answer_key", nullable=True)
    op.add_column("exercises", sa.Column("media", postgresql.JSONB(), nullable=True))
    op.add_column(
        "exercises",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_check_constraint("ck_exercises_teil", "exercises", "teil BETWEEN 1 AND 4")
    op.create_index("ix_exercises_skill_teil_created", "exercises", ["skill", "teil", "created_at"])

    # --- attempts ------------------------------------------------------------------------
    op.rename_table("reading_attempts", "attempts")
    op.execute("ALTER INDEX reading_attempts_pkey RENAME TO attempts_pkey")
    op.alter_column("attempts", "reading_exercise_id", new_column_name="exercise_id")
    op.execute(
        "ALTER TABLE attempts RENAME CONSTRAINT reading_attempts_reading_exercise_id_fkey TO attempts_exercise_id_fkey"
    )
    op.execute("ALTER TABLE attempts RENAME CONSTRAINT reading_attempts_user_id_fkey TO attempts_user_id_fkey")

    op.add_column(
        "attempts", sa.Column("status", attempt_status_enum, nullable=False, server_default="graded")
    )
    op.alter_column("attempts", "score", nullable=True, server_default=None)
    op.alter_column("attempts", "answers", nullable=True)
    op.alter_column("attempts", "is_correct_per_question", nullable=True)
    op.add_column("attempts", sa.Column("response_text", sa.Text(), nullable=True))
    op.add_column("attempts", sa.Column("audio_url", sa.String(1000), nullable=True))
    op.add_column("attempts", sa.Column("transcript", postgresql.JSONB(), nullable=True))
    op.add_column("attempts", sa.Column("rubric_scores", postgresql.JSONB(), nullable=True))
    op.add_column("attempts", sa.Column("feedback", postgresql.JSONB(), nullable=True))

    # --- jobs ----------------------------------------------------------------------------
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("kind", sa.String(100), nullable=False),
        sa.Column("status", job_status_enum, nullable=False, server_default="pending"),
        sa.Column("input", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error_code", sa.String(50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_table("jobs")

    # Lossy by necessity: the old schema can only hold Lesen exercises with objective scoring.
    op.execute("DELETE FROM attempts WHERE exercise_id IN (SELECT id FROM exercises WHERE skill <> 'lesen')")
    op.execute("DELETE FROM attempts WHERE score IS NULL OR answers IS NULL OR is_correct_per_question IS NULL")
    op.execute("DELETE FROM exercises WHERE skill <> 'lesen' OR answer_key IS NULL")

    for column in ("feedback", "rubric_scores", "transcript", "audio_url", "response_text", "status"):
        op.drop_column("attempts", column)
    op.alter_column("attempts", "is_correct_per_question", nullable=False)
    op.alter_column("attempts", "answers", nullable=False)
    op.alter_column("attempts", "score", nullable=False, server_default="0")
    op.execute("ALTER TABLE attempts RENAME CONSTRAINT attempts_user_id_fkey TO reading_attempts_user_id_fkey")
    op.execute(
        "ALTER TABLE attempts RENAME CONSTRAINT attempts_exercise_id_fkey TO reading_attempts_reading_exercise_id_fkey"
    )
    op.alter_column("attempts", "exercise_id", new_column_name="reading_exercise_id")
    op.execute("ALTER INDEX attempts_pkey RENAME TO reading_attempts_pkey")
    op.rename_table("attempts", "reading_attempts")

    op.drop_index("ix_exercises_skill_teil_created", table_name="exercises")
    op.drop_constraint("ck_exercises_teil", "exercises", type_="check")
    op.drop_column("exercises", "user_id")
    op.drop_column("exercises", "media")
    op.alter_column("exercises", "answer_key", nullable=False)

    exercise_type_enum.create(bind)
    op.add_column("exercises", sa.Column("exercise_type", exercise_type_enum, nullable=True))
    op.execute("UPDATE exercises SET exercise_type = (skill::text || '_teil' || teil::text)::exercise_type")
    op.alter_column("exercises", "exercise_type", nullable=False)
    op.drop_column("exercises", "teil")
    op.drop_column("exercises", "skill")
    op.execute("ALTER INDEX exercises_pkey RENAME TO reading_exercises_pkey")
    op.rename_table("exercises", "reading_exercises")

    job_status_enum.drop(bind)
    attempt_status_enum.drop(bind)
    skill_enum.drop(bind)
