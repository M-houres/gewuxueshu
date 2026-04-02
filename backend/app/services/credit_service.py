from sqlalchemy.orm import Session

from app.exceptions import BizError
from app.models import CreditTransaction, CreditType, User


def change_credits(
    db: Session,
    user: User,
    *,
    tx_type: CreditType,
    delta: int,
    reason: str,
    related_id: str | None = None,
    source: str | None = None,
    allow_negative: bool = False,
) -> CreditTransaction:
    if related_id:
        existed = (
            db.query(CreditTransaction)
            .filter(
                CreditTransaction.user_id == user.id,
                CreditTransaction.tx_type == tx_type,
                CreditTransaction.related_id == related_id,
            )
            .first()
        )
        if existed:
            return existed

    before = user.credits
    after = before + delta
    if not allow_negative and after < 0:
        raise BizError(code=4006, message="积分不足")
    user.credits = after
    tx = CreditTransaction(
        user_id=user.id,
        tx_type=tx_type,
        delta=delta,
        balance_before=before,
        balance_after=after,
        reason=reason,
        related_id=related_id,
        source=(source or getattr(user, "source", "") or "system"),
    )
    db.add(tx)
    db.flush()
    return tx
