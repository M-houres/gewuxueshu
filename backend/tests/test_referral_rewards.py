from sqlalchemy.orm import Session

from app.models import Order, ReferralRelation, ReferralReward, RewardType, User
from app.services.referral_service import grant_pay_rewards


def test_first_pay_referral_reward_does_not_grant_recurring(db_session: Session) -> None:
    inviter = User(phone="13800001000", nickname="inviter", source="web", credits=0)
    invitee = User(phone="13800001001", nickname="invitee", source="miniprogram", credits=0)
    db_session.add_all([inviter, invitee])
    db_session.flush()

    relation = ReferralRelation(
        inviter_id=inviter.id,
        invitee_id=invitee.id,
        invite_code="INVITE01",
        source="miniprogram",
        status="registered",
    )
    order = Order(
        order_no="ODFIRSTPAY001",
        user_id=invitee.id,
        amount_cny=9.9,
        credits=10000,
        source="miniprogram",
        status="paid",
        provider="mock",
        is_first_pay=True,
    )
    db_session.add_all([relation, order])
    db_session.flush()

    grant_pay_rewards(db_session, order)
    db_session.commit()

    rewards = (
        db_session.query(ReferralReward)
        .filter(ReferralReward.invitee_id == invitee.id)
        .order_by(ReferralReward.id.asc())
        .all()
    )
    assert [row.reward_type for row in rewards] == [RewardType.FIRST_PAY]
    assert rewards[0].source == "miniprogram"

    db_session.refresh(inviter)
    db_session.refresh(relation)
    assert inviter.credits == 1000
    assert relation.first_pay_reward_sent is True
    assert relation.status == "first_paid"


def test_recurring_pay_referral_reward_uses_recurring_type_only(db_session: Session) -> None:
    inviter = User(phone="13800001002", nickname="inviter", source="web", credits=0)
    invitee = User(phone="13800001003", nickname="invitee", source="miniprogram", credits=0)
    db_session.add_all([inviter, invitee])
    db_session.flush()

    relation = ReferralRelation(
        inviter_id=inviter.id,
        invitee_id=invitee.id,
        invite_code="INVITE02",
        source="miniprogram",
        status="first_paid",
        register_reward_sent=True,
        first_pay_reward_sent=True,
    )
    order = Order(
        order_no="ODRECUR001",
        user_id=invitee.id,
        amount_cny=39.0,
        credits=50000,
        source="miniprogram",
        status="paid",
        provider="mock",
        is_first_pay=False,
    )
    db_session.add_all([relation, order])
    db_session.flush()

    grant_pay_rewards(db_session, order)
    db_session.commit()

    rewards = db_session.query(ReferralReward).filter(ReferralReward.invitee_id == invitee.id).all()
    assert len(rewards) == 1
    assert rewards[0].reward_type == RewardType.RECURRING_PAY
    assert rewards[0].source == "miniprogram"

    db_session.refresh(inviter)
    assert inviter.credits == 2500
