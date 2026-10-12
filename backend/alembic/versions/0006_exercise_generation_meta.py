"""exercises.generation_meta: checker verification record

Revision ID: 0006_exercise_generation_meta
Revises: 0005_skill_agnostic_exercises
Create Date: 2026-10-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006_exercise_generation_meta"
down_revision: Union[str, None] = "0005_skill_agnostic_exercises"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("exercises", sa.Column("generation_meta", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("exercises", "generation_meta")
