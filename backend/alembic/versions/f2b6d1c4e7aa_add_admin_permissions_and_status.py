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


def upgrade() -> None:
    with op.batch_alter_table("admin_users") as batch_op:
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")))
        batch_op.add_column(sa.Column("permissions_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("admin_users") as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("permissions_json")
        batch_op.drop_column("is_active")
