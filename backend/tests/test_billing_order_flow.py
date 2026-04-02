from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.constants import DEFAULT_BILLING_PACKAGES
from app.deps import current_user, db_dep
from app.main import app
from app.models import Order, SystemConfig, User


def test_create_order_poll_and_pay_with_remote_provider(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr("app.worker_tasks.grant_order_referral_rewards_async.delay", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "app.api.billing.create_payment_session",
        lambda *_args, **_kwargs: {"provider": "wechat", "pay_url": "weixin://wxpay/mock"},
    )
    monkeypatch.setattr(
        "app.api.billing.query_remote_order_status",
        lambda *_args, **_kwargs: {"status": "paid", "amount_cny": 9.9},
    )

    user = User(phone="13800006666", nickname="u4", credits=0)
    db_session.add(user)
    db_session.add(
        SystemConfig(
            category="system",
            config_key="payment",
            config_value={
                "provider": "wechatpay_v3",
                "test_mode": False,
                "app_id": "wx123",
                "merchant_id": "1900000109",
                "merchant_serial_no": "SERIAL001",
                "merchant_private_key_pem": "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----",
                "api_v3_key": "12345678901234567890123456789012",
                "notify_url": "https://example.com",
            },
            updated_by=1,
        )
    )
    db_session.commit()
    db_session.refresh(user)

    app.dependency_overrides[current_user] = lambda: user
    try:
        create_resp = client.post("/api/v1/billing/create-order", json={"package_name": "入门包", "provider": "wechat"})
        assert create_resp.status_code == 200
        create_data = create_resp.json()["data"]
        order_no = create_data["order_no"]
        assert create_data["status"] == "created"

        status_resp = client.get(f"/api/v1/billing/order-status/{order_no}")
        assert status_resp.status_code == 200
        assert status_resp.json()["data"]["status"] == "paid"

        pay_resp = client.post(f"/api/v1/billing/order-pay/{order_no}")
        assert pay_resp.status_code == 200
        pay_data = pay_resp.json()["data"]
        assert pay_data["status"] == "paid"

        row = db_session.query(Order).filter(Order.order_no == order_no).first()
        assert row is not None
        assert row.status == "paid"
    finally:
        app.dependency_overrides.pop(current_user, None)


def test_payment_test_mode_switch_for_mock_provider(
    client: TestClient,
    db_session: Session,
) -> None:
    user = User(phone="13800007777", nickname="u5", credits=0)
    db_session.add(user)
    payment_cfg = SystemConfig(
        category="system",
        config_key="payment",
        config_value={"provider": "mock", "test_mode": True},
        updated_by=1,
    )
    db_session.add(payment_cfg)
    db_session.commit()
    db_session.refresh(user)

    app.dependency_overrides[current_user] = lambda: user
    try:
        ok_resp = client.post("/api/v1/billing/create-order", json={"package_name": "入门包", "provider": "mock"})
        assert ok_resp.status_code == 200

        payment_cfg.config_value = {"provider": "wechatpay_v3", "test_mode": False}
        db_session.commit()

        deny_resp = client.post("/api/v1/billing/create-order", json={"package_name": "入门包", "provider": "mock"})
        assert deny_resp.status_code == 400
    finally:
        app.dependency_overrides.pop(current_user, None)


def test_billing_packages_comes_from_admin_billing_config(
    client: TestClient,
    db_session: Session,
) -> None:
    user = User(phone="13800008888", nickname="u6", credits=0)
    db_session.add(user)
    db_session.add(
        SystemConfig(
            category="system",
            config_key="billing",
            config_value={
                "aigc_rate": 1,
                "dedup_rate": 2,
                "rewrite_rate": 2,
                "packages": [
                    {
                        "name": "运营体验包",
                        "price": 19.9,
                        "credits": 28000,
                        "description": "运营投放期体验套餐",
                        "badge": "限时",
                        "enabled": True,
                    },
                    {
                        "name": "停用套餐",
                        "price": 99.0,
                        "credits": 99999,
                        "enabled": False,
                    },
                ],
            },
            updated_by=1,
        )
    )
    db_session.add(
        SystemConfig(
            category="system",
            config_key="payment",
            config_value={"provider": "mock", "test_mode": True},
            updated_by=1,
        )
    )
    db_session.commit()
    db_session.refresh(user)

    app.dependency_overrides[current_user] = lambda: user
    try:
        pkg_resp = client.get("/api/v1/billing/packages")
        assert pkg_resp.status_code == 200
        items = pkg_resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["name"] == "运营体验包"
        assert items[0]["description"] == "运营投放期体验套餐"

        order_resp = client.post(
            "/api/v1/billing/create-order",
            json={"package_name": "运营体验包", "provider": "mock"},
        )
        assert order_resp.status_code == 200
        data = order_resp.json()["data"]
        assert data["amount_cny"] == 19.9
        assert data["credits"] == 28000
    finally:
        app.dependency_overrides.pop(current_user, None)


def test_unknown_error_handler_hides_internal_exception_detail(
    db_session: Session,
    monkeypatch,
) -> None:
    def _boom(*_args, **_kwargs):
        raise RuntimeError("LEAK_TEST_SECRET")

    monkeypatch.setattr("app.api.billing.create_payment_session", _boom)

    user = User(phone="13800009999", nickname="u7", credits=0)
    db_session.add(user)
    db_session.add(
        SystemConfig(
            category="system",
            config_key="payment",
            config_value={
                "provider": "wechatpay_v3",
                "test_mode": False,
                "app_id": "wx123",
                "merchant_id": "1900000109",
                "merchant_serial_no": "SERIAL001",
                "merchant_private_key_pem": "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----",
                "api_v3_key": "12345678901234567890123456789012",
                "notify_url": "https://example.com",
            },
            updated_by=1,
        )
    )
    db_session.commit()
    db_session.refresh(user)

    def override_db():
        yield db_session

    startup_handlers = list(app.router.on_startup)
    shutdown_handlers = list(app.router.on_shutdown)
    app.router.on_startup.clear()
    app.router.on_shutdown.clear()
    app.dependency_overrides[db_dep] = override_db
    app.dependency_overrides[current_user] = lambda: user
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(
                "/api/v1/billing/create-order",
                json={"package_name": DEFAULT_BILLING_PACKAGES[0]["name"], "provider": "wechat"},
            )
            assert resp.status_code == 500
            body = resp.json()
            assert body["code"] == 5000
            assert body["message"] == "服务器内部错误"
            assert "LEAK_TEST_SECRET" not in resp.text
    finally:
        app.dependency_overrides.pop(current_user, None)
        app.dependency_overrides.pop(db_dep, None)
        app.router.on_startup.extend(startup_handlers)
        app.router.on_shutdown.extend(shutdown_handlers)
