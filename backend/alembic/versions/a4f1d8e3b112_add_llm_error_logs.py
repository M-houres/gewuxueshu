"""add llm error logs

Revision ID: a4f1d8e3b112
Revises: bd2dc8a9c13c
Create Date: 2026-03-31 03:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a4f1d8e3b112"
down_revision: Union[str, None] = "bd2dc8a9c13c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_error_logs",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
        sa.Column("error_type", sa.String(length=60), nullable=False),
        sa.Column("error_detail", sa.String(length=500), nullable=False),
        sa.Column("trigger_downgrade", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_llm_error_logs_task_id"), "llm_error_logs", ["task_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_llm_error_logs_task_id"), table_name="llm_error_logs")
    op.drop_table("llm_error_logs")
