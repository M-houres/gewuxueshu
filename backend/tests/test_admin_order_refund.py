from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CreditTransaction, CreditType, Order, User


def test_admin_refund_paid_order(
    client: TestClient,
    db_session: Session,
    admin_override,
) -> None:
    user = User(phone="13800007777", nickname="u3", credits=10000)
    db_session.add(user)
    db_session.flush()

    order = Order(
        order_no="OD_REFUND_001",
        user_id=user.id,
        amount_cny=9.9,
        credits=10000,
        status="paid",
        provider="mock",
        is_first_pay=True,
    )
    db_session.add(order)
    db_session.add(
        CreditTransaction(
            user_id=user.id,
            tx_type=CreditType.PACKAGE_PAY,
            delta=10000,
            balance_before=0,
            balance_after=10000,
            reason="充值",
            related_id=order.order_no,
        )
    )
    db_session.commit()

    resp = client.post(f"/api/v1/admin/orders/{order.order_no}/refund")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "refunded"

    db_session.refresh(order)
    db_session.refresh(user)
    assert order.status == "refunded"
    assert user.credits == 0

    idempotent = client.post(f"/api/v1/admin/orders/{order.order_no}/refund")
    assert idempotent.status_code == 200
    assert idempotent.json()["data"]["idempotent"] is True
