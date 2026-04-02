from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import SystemConfig


def _readiness_item(client: TestClient, category: str) -> dict:
    resp = client.get("/api/v1/admin/configs/readiness")
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    return next(item for item in items if item["category"] == category)


def test_save_llm_config_for_domestic_provider(
    client: TestClient,
    admin_override,
) -> None:
    resp = client.post(
        "/api/v1/admin/configs/llm",
        json={
            "enabled": True,
            "provider": "qwen",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": "qwen-plus",
            "api_key": "sk-test-qwen",
            "timeout_seconds": 30,
            "max_output_tokens": 4096,
            "temperature": 0.2,
        },
    )
    assert resp.status_code == 200
    value = resp.json()["data"]["value"]
    assert value["provider"] == "qwen"
    assert value["model"] == "qwen-plus"

    readiness = _readiness_item(client, "llm")
    assert readiness["status"] == "ready"


def test_save_alipay_config_and_readiness_ready(
    client: TestClient,
    admin_override,
) -> None:
    resp = client.post(
        "/api/v1/admin/configs/payment",
        json={
            "provider": "alipay",
            "test_mode": False,
            "app_id": "2026000111111111",
            "gateway_url": "https://openapi.alipay.com/gateway.do",
            "notify_url": "https://pay.example.com/callback/alipay",
            "app_private_key_pem": "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----",
            "alipay_public_key": "-----BEGIN PUBLIC KEY-----\nxyz\n-----END PUBLIC KEY-----",
        },
    )
    assert resp.status_code == 200
    value = resp.json()["data"]["value"]
    assert value["provider"] == "alipay"
    assert value["api_key"].startswith("-----BEGIN PRIVATE KEY-----")

    readiness = _readiness_item(client, "payment")
    assert readiness["status"] == "ready"


def test_reject_unsupported_gateway_proxy_payment_config(
    client: TestClient,
    admin_override,
) -> None:
    resp = client.post(
        "/api/v1/admin/configs/payment",
        json={
            "provider": "gateway_proxy",
            "test_mode": False,
            "notify_url": "https://pay.example.com/callback",
        },
    )
    assert resp.status_code == 400
    assert "payment.provider" in resp.json()["message"]


def test_payment_readiness_flags_legacy_alipay_missing_public_key(
    client: TestClient,
    db_session: Session,
    admin_override,
) -> None:
    db_session.add(
        SystemConfig(
            category="system",
            config_key="payment",
            config_value={
                "provider": "alipay",
                "test_mode": False,
                "app_id": "2026000222222222",
                "notify_url": "https://pay.example.com/callback/alipay",
                "app_private_key_pem": "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----",
            },
            updated_by=1,
        )
    )
    db_session.commit()

    readiness = _readiness_item(client, "payment")
    assert readiness["status"] == "error"
    assert "alipay_public_key" in readiness["message"]


def test_payment_readiness_flags_legacy_gateway_proxy_as_unsupported(
    client: TestClient,
    db_session: Session,
    admin_override,
) -> None:
    db_session.add(
        SystemConfig(
            category="system",
            config_key="payment",
            config_value={
                "provider": "gateway_proxy",
                "test_mode": False,
                "notify_url": "https://pay.example.com/callback",
            },
            updated_by=1,
        )
    )
    db_session.commit()

    readiness = _readiness_item(client, "payment")
    assert readiness["status"] == "error"
    assert "不支持" in readiness["message"]


def test_reject_private_notify_url_for_real_wechat_payment(
    client: TestClient,
    admin_override,
) -> None:
    resp = client.post(
        "/api/v1/admin/configs/payment",
        json={
            "provider": "wechatpay_v3",
            "test_mode": False,
            "app_id": "wx1234567890",
            "merchant_id": "1900000109",
            "merchant_serial_no": "SERIAL123456",
            "merchant_private_key_pem": "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----",
            "api_v3_key": "12345678901234567890123456789012",
            "notify_url": "https://127.0.0.1:8100/api/v1/billing/notify/wechatpay",
        },
    )
    assert resp.status_code == 400
    body = resp.json()
    assert "公网 HTTPS" in body["message"]


def test_save_billing_with_packages_affects_public_package_list(
    client: TestClient,
    admin_override,
) -> None:
    resp = client.post(
        "/api/v1/admin/configs/billing",
        json={
            "aigc_rate": 1,
            "dedup_rate": 3,
            "rewrite_rate": 4,
            "packages": [
                {
                    "name": "校园体验包",
                    "price": 29.9,
                    "credits": 42000,
                    "description": "用于毕业季密集检测",
                    "badge": "热销",
                    "enabled": True,
                },
                {
                    "name": "隐藏套餐",
                    "price": 88.0,
                    "credits": 88000,
                    "enabled": False,
                },
            ],
        },
    )
    assert resp.status_code == 200
    value = resp.json()["data"]["value"]
    assert value["dedup_rate"] == 3
    assert len(value["packages"]) == 2

    pkg_resp = client.get("/api/v1/billing/packages")
    assert pkg_resp.status_code == 200
    items = pkg_resp.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["name"] == "校园体验包"
    assert items[0]["credits"] == 42000
