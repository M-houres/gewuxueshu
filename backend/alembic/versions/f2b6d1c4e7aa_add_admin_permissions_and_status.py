"""add admin permissions and status

Revision ID: f2b6d1c4e7aa
Revises: c7f4e2ad91fb
Create Date: 2026-04-03 18:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2b6d1c4e7aa"
down_revision: Union[str, None] = "c7f4e2ad91fb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    existing = _existing_columns("admin_users")
    with op.batch_alter_table("admin_users") as batch_op:
        if "is_active" not in existing:
            batch_op.add_column(
                sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1"))
            )
        if "permissions_json" not in existing:
            batch_op.add_column(
                sa.Column("permissions_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))
            )
        if "updated_at" not in existing:
            batch_op.add_column(
                sa.Column(
                    "updated_at",
                    sa.DateTime(),
                    nullable=False,
                    server_default=sa.text("(CURRENT_TIMESTAMP)"),
                )
            )


def downgrade() -> None:
    existing = _existing_columns("admin_users")
    with op.batch_alter_table("admin_users") as batch_op:
        if "updated_at" in existing:
            batch_op.drop_column("updated_at")
        if "permissions_json" in existing:
            batch_op.drop_column("permissions_json")
        if "is_active" in existing:
            batch_op.drop_column("is_active")
