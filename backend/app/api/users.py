import base64
from io import BytesIO

import qrcode
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.deps import current_user, db_dep
from app.models import CreditTransaction, Notification, ReferralRelation, ReferralReward, User, UserInviteCode
from app.pagination import paginate
from app.responses import ok
from app.schemas import APIResp
from app.services.referral_service import mask_phone

router = APIRouter()


def _build_invite_qrcode(link: str) -> str:
    img = qrcode.make(link)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _frontend_base_url(request: Request) -> str:
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
    forwarded_host = request.headers.get("x-forwarded-host", "").split(",")[0].strip()
    if forwarded_host:
        scheme = forwarded_proto or request.url.scheme or "https"
        return f"{scheme}://{forwarded_host}".rstrip("/")
    return str(request.base_url).rstrip("/")


@router.get("/me", response_model=APIResp)
def me(user: User = Depends(current_user)) -> APIResp:
    return ok(
        data={
            "id": user.id,
            "phone": user.phone,
            "nickname": user.nickname,
            "credits": user.credits,
            "source": user.source,
            "created_at": user.created_at,
        }
    )


@router.patch("/me", response_model=APIResp)
def update_me(
    payload: dict,
    user: User = Depends(current_user),
    db: Session = Depends(db_dep),
) -> APIResp:
    nickname = str(payload.get("nickname", "")).strip()
    if nickname:
        user.nickname = nickname[:64]
        db.commit()
    return ok(
        data={
            "id": user.id,
            "phone": user.phone,
            "nickname": user.nickname,
            "credits": user.credits,
            "source": user.source,
            "created_at": user.created_at,
        }
    )


@router.get("/me/invite-code", response_model=APIResp)
def my_invite_code(request: Request, user: User = Depends(current_user), db: Session = Depends(db_dep)) -> APIResp:
    row = db.query(UserInviteCode).filter(UserInviteCode.user_id == user.id).first()
    if row is None:
        row = UserInviteCode(user_id=user.id, invite_code=f"U{user.id:07d}")
        db.add(row)
        db.commit()
    base = _frontend_base_url(request) + "/register"
    link = f"{base}?ref={row.invite_code}"
    return ok(data={"invite_code": row.invite_code, "invite_link": link, "qrcode_data_url": _build_invite_qrcode(link)})


@router.get("/me/invite-qrcode", response_model=APIResp)
def my_invite_qrcode(request: Request, user: User = Depends(current_user), db: Session = Depends(db_dep)) -> APIResp:
    row = db.query(UserInviteCode).filter(UserInviteCode.user_id == user.id).first()
    if row is None:
        row = UserInviteCode(user_id=user.id, invite_code=f"U{user.id:07d}")
        db.add(row)
        db.commit()

    link = f"{_frontend_base_url(request)}/register?ref={row.invite_code}"
    return ok(
        data={
            "invite_code": row.invite_code,
            "invite_link": link,
            "qrcode_data_url": _build_invite_qrcode(link),
        }
    )


@router.get("/me/credit-transactions", response_model=APIResp)
def my_credit_transactions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tx_type: str | None = Query(default=None),
    user: User = Depends(current_user),
    db: Session = Depends(db_dep),
) -> APIResp:
    base_query = db.query(CreditTransaction).filter(CreditTransaction.user_id == user.id)
    if tx_type:
        base_query = base_query.filter(CreditTransaction.tx_type == tx_type)
    total = base_query.count()
    rows = (
        base_query.order_by(desc(CreditTransaction.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        {
            "id": row.id,
            "tx_type": row.tx_type.value,
            "delta": row.delta,
            "balance_before": row.balance_before,
            "balance_after": row.balance_after,
                "reason": row.reason,
                "related_id": row.related_id,
                "source": row.source,
                "created_at": row.created_at,
            }
        for row in rows
    ]
    return ok(data={"items": items, "pagination": paginate(total, page, page_size)})


@router.get("/me/referrals", response_model=APIResp)
def my_referrals(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(db_dep),
) -> APIResp:
    base_query = (
        db.query(ReferralRelation, User.phone)
        .join(User, User.id == ReferralRelation.invitee_id)
        .filter(ReferralRelation.inviter_id == user.id)
    )
    total = base_query.count()
    rows = (
        base_query.order_by(desc(ReferralRelation.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = []
    for relation, phone in rows:
        reward_sum = (
            db.query(func.coalesce(func.sum(ReferralReward.credits), 0))
            .filter(
                ReferralReward.inviter_id == user.id,
                ReferralReward.invitee_id == relation.invitee_id,
            )
            .scalar()
            or 0
        )
        items.append(
            {
                "invitee_id": relation.invitee_id,
                "invitee_phone_masked": mask_phone(phone),
                "status": relation.status,
                "source": relation.source,
                "created_at": relation.created_at,
                "reward_credits": int(reward_sum),
            }
        )
    return ok(data={"items": items, "pagination": paginate(total, page, page_size)})


@router.get("/me/referral-rewards", response_model=APIResp)
def my_referral_rewards(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(db_dep),
) -> APIResp:
    base_query = db.query(ReferralReward).filter(
        (ReferralReward.inviter_id == user.id) | (ReferralReward.invitee_id == user.id)
    )
    total = base_query.count()
    rows = (
        base_query.order_by(desc(ReferralReward.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = []
    for row in rows:
        role = "邀请人奖励" if row.inviter_id == user.id else "被邀请福利"
        items.append(
            {
                "id": row.id,
                "role": role,
                "invitee_id": row.invitee_id,
                "reward_type": row.reward_type.value,
                "credits": row.credits,
                "status": row.status,
                "source": row.source,
                "created_at": row.created_at,
            }
        )
    return ok(data={"items": items, "pagination": paginate(total, page, page_size)})


@router.get("/me/notifications", response_model=APIResp)
def my_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(db_dep),
) -> APIResp:
    base_query = db.query(Notification).filter(Notification.user_id == user.id)
    total = base_query.count()
    rows = (
        base_query.order_by(desc(Notification.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        {
            "id": n.id,
            "title": n.title,
            "content": n.content,
            "is_read": n.is_read,
            "created_at": n.created_at,
        }
        for n in rows
    ]
    return ok(data={"items": items, "pagination": paginate(total, page, page_size)})
