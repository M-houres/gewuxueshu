from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

ID_PK_TYPE = BigInteger().with_variant(Integer, "sqlite")


class TaskType(str, Enum):
    AIGC_DETECT = "aigc_detect"
    DEDUP = "dedup"
    REWRITE = "rewrite"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RewardType(str, Enum):
    REGISTER_INVITE = "register_invite"
    REGISTER_BONUS = "register_bonus"
    FIRST_PAY = "first_pay"
    RECURRING_PAY = "recurring_pay"


class CreditType(str, Enum):
    INIT = "init"
    TASK_CONSUME = "task_consume"
    TASK_REFUND = "task_refund"
    PACKAGE_PAY = "package_pay"
    REFERRAL_INVITE = "referral_invite"
    REFERRAL_BONUS = "referral_bonus"
    REFERRAL_FIRST_PAY = "referral_first_pay"
    REFERRAL_RECURRING = "referral_recurring"
    ADMIN_ADJUST = "admin_adjust"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(ID_PK_TYPE, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    nickname: Mapped[str] = mapped_column(String(64), default="")
    openid: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    wechat_unionid: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    wechat_openid_web: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    wechat_openid_mp: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(20), default="web", index=True)
    credits: Mapped[int] = mapped_column(Integer, default=0)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    tasks: Mapped[list["Task"]] = relationship(back_populates="user")


class UserInviteCode(Base):
    __tablename__ = "user_invite_codes"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    invite_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ReferralRelation(Base):
    __tablename__ = "referral_relations"

    id: Mapped[int] = mapped_column(ID_PK_TYPE, primary_key=True, autoincrement=True)
    inviter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    invitee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    invite_code: Mapped[str] = mapped_column(String(16), index=True)
    source: Mapped[str] = mapped_column(String(20), default="web", index=True)
    status: Mapped[str] = mapped_column(String(20), default="registered")
    register_reward_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    first_pay_reward_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ReferralReward(Base):
    __tablename__ = "referral_rewards"

    id: Mapped[int] = mapped_column(ID_PK_TYPE, primary_key=True, autoincrement=True)
    inviter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    invitee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    reward_type: Mapped[RewardType] = mapped_column(SQLEnum(RewardType), index=True)
    reward_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    credits: Mapped[int] = mapped_column(Integer)
    ref_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="web", index=True)
    status: Mapped[str] = mapped_column(String(16), default="sent")
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(ID_PK_TYPE, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount_cny: Mapped[float] = mapped_column(Float)
    credits: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(20), default="web", index=True)
    status: Mapped[str] = mapped_column(String(20), default="created")
    provider: Mapped[str] = mapped_column(String(20), default="mock")
    is_first_pay: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id: Mapped[int] = mapped_column(ID_PK_TYPE, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    tx_type: Mapped[CreditType] = mapped_column(SQLEnum(CreditType), index=True)
    delta: Mapped[int] = mapped_column(Integer)
    balance_before: Mapped[int] = mapped_column(Integer)
    balance_after: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(255), default="")
    related_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(20), default="web", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "tx_type", "related_id", name="uk_user_tx_related"),
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(ID_PK_TYPE, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    task_type: Mapped[TaskType] = mapped_column(SQLEnum(TaskType), index=True)
    platform: Mapped[str] = mapped_column(String(20), index=True)
    processing_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="web", index=True)
    status: Mapped[TaskStatus] = mapped_column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    source_filename: Mapped[str] = mapped_column(String(255))
    source_path: Mapped[str] = mapped_column(String(500))
    report_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    output_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    cost_credits: Mapped[int] = mapped_column(Integer, default=0)
    refund_done: Mapped[bool] = mapped_column(Boolean, default=False)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship(back_populates="tasks")


class SystemSwitch(Base):
    __tablename__ = "system_switch"

    id: Mapped[int] = mapped_column(ID_PK_TYPE, primary_key=True, autoincrement=True)
    current_mode: Mapped[str] = mapped_column(String(32), default="LLM_PLUS_ALGO")
    llm_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    llm_fail_count: Mapped[int] = mapped_column(Integer, default=0)
    llm_fail_threshold: Mapped[int] = mapped_column(Integer, default=3)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class SwitchLog(Base):
    __tablename__ = "switch_logs"

    id: Mapped[int] = mapped_column(ID_PK_TYPE, primary_key=True, autoincrement=True)
    from_mode: Mapped[str] = mapped_column(String(32))
    to_mode: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class LLMErrorLog(Base):
    __tablename__ = "llm_error_logs"

    id: Mapped[int] = mapped_column(ID_PK_TYPE, primary_key=True, autoincrement=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True, index=True)
    error_type: Mapped[str] = mapped_column(String(60))
    error_detail: Mapped[str] = mapped_column(String(500))
    trigger_downgrade: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(ID_PK_TYPE, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="operator")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    permissions_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(ID_PK_TYPE, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    content: Mapped[str] = mapped_column(String(500))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RegistrationRiskLog(Base):
    __tablename__ = "registration_risk_logs"

    id: Mapped[int] = mapped_column(ID_PK_TYPE, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)
    ip: Mapped[str] = mapped_column(String(64), index=True)
    user_agent: Mapped[str] = mapped_column(String(300), default="")
    reason: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SystemConfig(Base):
    __tablename__ = "system_configs"

    id: Mapped[int] = mapped_column(ID_PK_TYPE, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(60), index=True)
    config_key: Mapped[str] = mapped_column(String(60), index=True)
    config_value: Mapped[dict] = mapped_column(JSON)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("category", "config_key", name="uk_cfg_category_key"),
    )


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[int] = mapped_column(ID_PK_TYPE, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("admin_users.id"), index=True)
    action: Mapped[str] = mapped_column(String(80))
    target_type: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[str] = mapped_column(String(120), default="")
    before_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
