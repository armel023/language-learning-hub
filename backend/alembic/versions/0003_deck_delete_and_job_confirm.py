"""deck delete keeps cards + extraction job confirm guard

Revision ID: 0003_deck_delete_and_job_confirm
Revises: 0002_study_sessions
Create Date: 2026-10-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_deck_delete_and_job_confirm"
down_revision: Union[str, None] = "0002_study_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Postgres' default name for the unnamed FK created in 0001_initial_schema.
DECK_FK = "vocabulary_items_deck_id_fkey"


def upgrade() -> None:
    op.drop_constraint(DECK_FK, "vocabulary_items", type_="foreignkey")
    op.create_foreign_key(
        DECK_FK, "vocabulary_items", "decks", ["deck_id"], ["id"], ondelete="SET NULL"
    )

    op.add_column(
        "vocab_extraction_jobs",
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vocab_extraction_jobs", "confirmed_at")

    op.drop_constraint(DECK_FK, "vocabulary_items", type_="foreignkey")
    op.create_foreign_key(DECK_FK, "vocabulary_items", "decks", ["deck_id"], ["id"])
