"""add task processing mode

Revision ID: e1a9c4d8b7f3
Revises: f2b6d1c4e7aa
Create Date: 2026-04-04 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1a9c4d8b7f3"
down_revision: Union[str, None] = "f2b6d1c4e7aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    existing = _existing_columns("tasks")
    if "processing_mode" in existing:
        return
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(sa.Column("processing_mode", sa.String(length=32), nullable=True))


def downgrade() -> None:
    existing = _existing_columns("tasks")
    if "processing_mode" not in existing:
        return
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_column("processing_mode")
