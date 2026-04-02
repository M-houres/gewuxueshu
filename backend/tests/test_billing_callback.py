from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CreditTransaction, Order, SystemConfig, User
from app.services.payment_service import sign_payload


def test_payment_callback_signature_and_idempotency(
    client: TestClient,
    db_session: Session,
    settings_override,
    monkeypatch,
) -> None:
    monkeypatch.setattr("app.worker_tasks.grant_order_referral_rewards_async.delay", lambda *_args, **_kwargs: None)

    user = User(phone="13800000001", nickname="测试用户", credits=0)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    payload = {
        "order_no": "ODCALLBACK0001",
        "user_id": user.id,
        "package_name": "入门包",
        "amount_cny": 9.9,
        "paid_at": int(datetime.now(timezone.utc).timestamp()),
        "status": "paid",
        "provider": "wechat",
        "nonce": "nonce-001",
    }
    sign = sign_payload(payload)

    resp = client.post("/api/v1/billing/callback", json={**payload, "sign": sign})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "paid"
    assert data["idempotent"] is False

    db_session.refresh(user)
    assert user.credits == 10000
    assert db_session.query(Order).filter(Order.order_no == payload["order_no"]).count() == 1
    assert (
        db_session.query(CreditTransaction).filter(CreditTransaction.related_id == payload["order_no"]).count() == 1
    )

    resp2 = client.post("/api/v1/billing/callback", json={**payload, "sign": sign})
    assert resp2.status_code == 200
    data2 = resp2.json()["data"]
    assert data2["idempotent"] is True
    db_session.refresh(user)
    assert user.credits == 10000
    assert (
        db_session.query(CreditTransaction).filter(CreditTransaction.related_id == payload["order_no"]).count() == 1
    )


def test_payment_callback_rejects_invalid_signature(
    client: TestClient,
    db_session: Session,
    settings_override,
) -> None:
    user = User(phone="13800000002", nickname="测试用户2", credits=0)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    payload = {
        "order_no": "ODCALLBACK0002",
        "user_id": user.id,
        "package_name": "入门包",
        "amount_cny": 9.9,
        "paid_at": int(datetime.now(timezone.utc).timestamp()),
        "status": "paid",
        "provider": "wechat",
        "nonce": "nonce-002",
        "sign": "deadbeefdeadbeefdeadbeefdeadbeef",
    }
    resp = client.post("/api/v1/billing/callback", json=payload)
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 4204


def test_payment_callback_uses_payment_config_secret(
    client: TestClient,
    db_session: Session,
    settings_override,
    monkeypatch,
) -> None:
    monkeypatch.setattr("app.worker_tasks.grant_order_referral_rewards_async.delay", lambda *_args, **_kwargs: None)

    db_session.add(
        SystemConfig(
            category="system",
            config_key="payment",
            config_value={
                "provider": "wechat",
                "app_id": "",
                "merchant_id": "",
                "api_key": "",
                "callback_secret": "db_callback_secret_001",
            },
        )
    )
    user = User(phone="13800000003", nickname="测试用户3", credits=0)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    payload = {
        "order_no": "ODCALLBACK0003",
        "user_id": user.id,
        "package_name": "入门包",
        "amount_cny": 9.9,
        "paid_at": int(datetime.now(timezone.utc).timestamp()),
        "status": "paid",
        "provider": "wechat",
        "nonce": "nonce-003",
    }
    sign = sign_payload(payload, db=db_session)
    resp = client.post("/api/v1/billing/callback", json={**payload, "sign": sign})
    assert resp.status_code == 200
