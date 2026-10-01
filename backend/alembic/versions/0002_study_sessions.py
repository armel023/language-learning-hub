"""study session tracking + search/pagination support

Revision ID: 0002_study_sessions
Revises: 0001_initial_schema
Create Date: 2026-10-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_study_sessions"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("study_session_count", sa.Integer(), nullable=False, server_default="0"),
    )

    op.add_column(
        "vocabulary_items",
        sa.Column("incorrect_hard_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "vocabulary_items",
        sa.Column("incorrect_moderate_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "vocabulary_items",
        sa.Column("study_due_at_session", sa.Integer(), nullable=True),
    )
    op.drop_column("vocabulary_items", "next_due_at")
    op.drop_column("vocabulary_items", "ease_factor")
    op.drop_column("vocabulary_items", "interval_days")


def downgrade() -> None:
    op.add_column(
        "vocabulary_items",
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "vocabulary_items",
        sa.Column("ease_factor", sa.Float(), nullable=False, server_default="2.5"),
    )
    op.add_column(
        "vocabulary_items",
        sa.Column("next_due_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.drop_column("vocabulary_items", "study_due_at_session")
    op.drop_column("vocabulary_items", "incorrect_moderate_count")
    op.drop_column("vocabulary_items", "incorrect_hard_count")

    op.drop_column("users", "study_session_count")
