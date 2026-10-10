"""ai_runs: per-run token usage for budgets and monitoring

Revision ID: 0004_ai_runs
Revises: 0003_deck_delete_and_job_confirm
Create Date: 2026-10-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_ai_runs"
down_revision: Union[str, None] = "0003_deck_delete_and_job_confirm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("feature", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model_name", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("succeeded", "failed", "budget_exceeded", name="ai_run_status"),
            nullable=False,
        ),
        sa.Column("requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("trace_id", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ai_runs_user_created", "ai_runs", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_runs_user_created", table_name="ai_runs")
    op.drop_table("ai_runs")
    sa.Enum(name="ai_run_status").drop(op.get_bind(), checkfirst=True)
