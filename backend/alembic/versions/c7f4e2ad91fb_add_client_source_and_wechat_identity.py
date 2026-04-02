"""add client source and wechat identity

Revision ID: c7f4e2ad91fb
Revises: a4f1d8e3b112
Create Date: 2026-04-02 11:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7f4e2ad91fb"
down_revision: Union[str, None] = "a4f1d8e3b112"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("wechat_unionid", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("wechat_openid_web", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("wechat_openid_mp", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("source", sa.String(length=20), nullable=False, server_default="web"))
        batch_op.create_index(batch_op.f("ix_users_wechat_unionid"), ["wechat_unionid"], unique=False)
        batch_op.create_index(batch_op.f("ix_users_wechat_openid_web"), ["wechat_openid_web"], unique=False)
        batch_op.create_index(batch_op.f("ix_users_wechat_openid_mp"), ["wechat_openid_mp"], unique=False)
        batch_op.create_index(batch_op.f("ix_users_source"), ["source"], unique=False)

    op.execute("UPDATE users SET wechat_openid_web = openid WHERE openid IS NOT NULL AND wechat_openid_web IS NULL")

    with op.batch_alter_table("credit_transactions") as batch_op:
        batch_op.add_column(sa.Column("source", sa.String(length=20), nullable=False, server_default="web"))
        batch_op.create_index(batch_op.f("ix_credit_transactions_source"), ["source"], unique=False)

    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("source", sa.String(length=20), nullable=False, server_default="web"))
        batch_op.create_index(batch_op.f("ix_orders_source"), ["source"], unique=False)

    with op.batch_alter_table("referral_relations") as batch_op:
        batch_op.add_column(sa.Column("source", sa.String(length=20), nullable=False, server_default="web"))
        batch_op.create_index(batch_op.f("ix_referral_relations_source"), ["source"], unique=False)

    with op.batch_alter_table("referral_rewards") as batch_op:
        batch_op.add_column(sa.Column("source", sa.String(length=20), nullable=False, server_default="web"))
        batch_op.create_index(batch_op.f("ix_referral_rewards_source"), ["source"], unique=False)

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(sa.Column("source", sa.String(length=20), nullable=False, server_default="web"))
        batch_op.create_index(batch_op.f("ix_tasks_source"), ["source"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_index(batch_op.f("ix_tasks_source"))
        batch_op.drop_column("source")

    with op.batch_alter_table("referral_rewards") as batch_op:
        batch_op.drop_index(batch_op.f("ix_referral_rewards_source"))
        batch_op.drop_column("source")

    with op.batch_alter_table("referral_relations") as batch_op:
        batch_op.drop_index(batch_op.f("ix_referral_relations_source"))
        batch_op.drop_column("source")

    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_index(batch_op.f("ix_orders_source"))
        batch_op.drop_column("source")

    with op.batch_alter_table("credit_transactions") as batch_op:
        batch_op.drop_index(batch_op.f("ix_credit_transactions_source"))
        batch_op.drop_column("source")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_source"))
        batch_op.drop_index(batch_op.f("ix_users_wechat_openid_mp"))
        batch_op.drop_index(batch_op.f("ix_users_wechat_openid_web"))
        batch_op.drop_index(batch_op.f("ix_users_wechat_unionid"))
        batch_op.drop_column("source")
        batch_op.drop_column("wechat_openid_mp")
        batch_op.drop_column("wechat_openid_web")
        batch_op.drop_column("wechat_unionid")
