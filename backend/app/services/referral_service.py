from datetime import datetime

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    CreditType,
    Notification,
    Order,
    ReferralRelation,
    ReferralReward,
    RewardType,
    SystemConfig,
    User,
    UserInviteCode,
)
from app.services.credit_service import change_credits

settings = get_settings()


def get_referral_rules(db: Session) -> dict:
    cfg = (
        db.query(SystemConfig)
        .filter(SystemConfig.category == "referral", SystemConfig.config_key == "rules")
        .first()
    )
    if cfg:
        return cfg.config_value
    default = {
        "register_inviter_credits": settings.referral_register_inviter_credits,
        "register_invitee_bonus": settings.referral_register_invitee_bonus,
        "first_pay_ratio": 0.1,
        "recurring_ratio": 0.05,
        "ip_limit_24h": 3,
    }
    cfg = SystemConfig(category="referral", config_key="rules", config_value=default)
    db.add(cfg)
    db.flush()
    return default


def update_referral_rules(db: Session, values: dict, admin_id: int) -> dict:
    cfg = (
        db.query(SystemConfig)
        .filter(SystemConfig.category == "referral", SystemConfig.config_key == "rules")
        .first()
    )
    if cfg is None:
        cfg = SystemConfig(category="referral", config_key="rules", config_value=values, updated_by=admin_id)
        db.add(cfg)
    else:
        cfg.config_value = values
        cfg.updated_by = admin_id
    db.flush()
    return values


def get_inviter_by_code(db: Session, invite_code: str) -> User | None:
    row = db.query(UserInviteCode).filter(UserInviteCode.invite_code == invite_code).first()
    if not row:
        return None
    return db.get(User, row.user_id)


def bind_referral_relation(
    db: Session,
    *,
    invitee: User,
    referrer_code: str,
    source: str = "web",
) -> ReferralRelation | None:
    inviter = get_inviter_by_code(db, referrer_code)
    if not inviter or inviter.id == invitee.id or inviter.is_banned:
        return None
    existed = db.query(ReferralRelation).filter(ReferralRelation.invitee_id == invitee.id).first()
    if existed:
        return existed
    relation = ReferralRelation(
        inviter_id=inviter.id,
        invitee_id=invitee.id,
        invite_code=referrer_code,
        source=source or getattr(invitee, "source", "") or "web",
        status="registered",
    )
    db.add(relation)
    db.flush()
    return relation


def grant_register_rewards(db: Session, relation: ReferralRelation) -> None:
    if relation.register_reward_sent:
        return
    rules = get_referral_rules(db)
    inviter = db.get(User, relation.inviter_id)
    invitee = db.get(User, relation.invitee_id)
    if not inviter or not invitee:
        return

    inviter_reward = int(rules.get("register_inviter_credits", settings.referral_register_inviter_credits))
    invitee_reward = int(rules.get("register_invitee_bonus", settings.referral_register_invitee_bonus))
    reward_source = relation.source or getattr(invitee, "source", "") or getattr(inviter, "source", "") or "web"

    inviter_key = f"register_invite:{invitee.id}"
    inviter_row = db.query(ReferralReward).filter(ReferralReward.reward_key == inviter_key).first()
    if inviter_row is None and inviter_reward > 0:
        db.add(
            ReferralReward(
                inviter_id=inviter.id,
                invitee_id=invitee.id,
                reward_type=RewardType.REGISTER_INVITE,
                reward_key=inviter_key,
                credits=inviter_reward,
                source=reward_source,
                status="sent",
                sent_at=datetime.utcnow(),
            )
        )
        change_credits(
            db,
            inviter,
            tx_type=CreditType.REFERRAL_INVITE,
            delta=inviter_reward,
            reason="invite_register_reward",
            related_id=inviter_key,
            source=reward_source,
        )
        db.add(
            Notification(
                user_id=inviter.id,
                title="邀请奖励到账",
                content=f"您通过邀请新用户注册获得 {inviter_reward} 积分",
            )
        )

    invitee_key = f"register_bonus:{invitee.id}"
    invitee_row = db.query(ReferralReward).filter(ReferralReward.reward_key == invitee_key).first()
    if invitee_row is None and invitee_reward > 0:
        db.add(
            ReferralReward(
                inviter_id=inviter.id,
                invitee_id=invitee.id,
                reward_type=RewardType.REGISTER_BONUS,
                reward_key=invitee_key,
                credits=invitee_reward,
                source=reward_source,
                status="sent",
                sent_at=datetime.utcnow(),
            )
        )
        change_credits(
            db,
            invitee,
            tx_type=CreditType.REFERRAL_BONUS,
            delta=invitee_reward,
            reason="invitee_register_bonus",
            related_id=invitee_key,
            source=reward_source,
        )
        db.add(
            Notification(
                user_id=invitee.id,
                title="注册福利到账",
                content=f"您获得注册福利 {invitee_reward} 积分",
            )
        )

    relation.register_reward_sent = True
    db.flush()


def grant_pay_rewards(db: Session, order: Order) -> None:
    relation = (
        db.query(ReferralRelation)
        .filter(ReferralRelation.invitee_id == order.user_id)
        .with_for_update()
        .first()
    )
    if relation is None:
        return
    inviter = db.get(User, relation.inviter_id)
    if inviter is None or inviter.is_banned:
        return

    rules = get_referral_rules(db)
    first_ratio = float(rules.get("first_pay_ratio", 0.1))
    recurring_ratio = float(rules.get("recurring_ratio", 0.05))
    reward_source = order.source or relation.source or getattr(inviter, "source", "") or "web"

    if order.is_first_pay:
        if not relation.first_pay_reward_sent:
            first_reward = int(order.credits * first_ratio)
            first_key = f"first_pay:{order.user_id}"
            existed = db.query(ReferralReward).filter(ReferralReward.reward_key == first_key).first()
            if first_reward > 0 and existed is None:
                db.add(
                    ReferralReward(
                        inviter_id=inviter.id,
                        invitee_id=order.user_id,
                        reward_type=RewardType.FIRST_PAY,
                        reward_key=first_key,
                        credits=first_reward,
                        ref_order_id=order.order_no,
                        source=reward_source,
                        status="sent",
                        sent_at=datetime.utcnow(),
                    )
                )
                change_credits(
                    db,
                    inviter,
                    tx_type=CreditType.REFERRAL_FIRST_PAY,
                    delta=first_reward,
                    reason="invite_first_pay_reward",
                    related_id=first_key,
                    source=reward_source,
                )
                db.add(
                    Notification(
                        user_id=inviter.id,
                        title="首充奖励到账",
                        content=f"您因好友首充获得 {first_reward} 积分奖励",
                    )
                )
        relation.first_pay_reward_sent = True
        relation.status = "first_paid"
        db.flush()
        return

    recurring_reward = int(order.credits * recurring_ratio)
    recurring_key = f"recurring_pay:{order.user_id}:{order.order_no}"
    existed = db.query(ReferralReward).filter(ReferralReward.reward_key == recurring_key).first()
    if recurring_reward > 0 and existed is None:
        db.add(
            ReferralReward(
                inviter_id=inviter.id,
                invitee_id=order.user_id,
                reward_type=RewardType.RECURRING_PAY,
                reward_key=recurring_key,
                credits=recurring_reward,
                ref_order_id=order.order_no,
                source=reward_source,
                status="sent",
                sent_at=datetime.utcnow(),
            )
        )
        change_credits(
            db,
            inviter,
            tx_type=CreditType.REFERRAL_RECURRING,
            delta=recurring_reward,
            reason="invite_recurring_reward",
            related_id=recurring_key,
            source=reward_source,
        )
        db.add(
            Notification(
                user_id=inviter.id,
                title="返佣奖励到账",
                content=f"您因好友充值获得 {recurring_reward} 积分奖励",
            )
        )
    db.flush()


def mask_phone(phone: str) -> str:
    if len(phone) < 7:
        return phone
    return f"{phone[:3]}****{phone[-4:]}"
