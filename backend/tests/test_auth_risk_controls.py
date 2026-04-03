from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import worker_tasks
from app.models import RegistrationRiskLog, SystemConfig, User, UserInviteCode


def _login_with_code(
    client: TestClient,
    *,
    phone: str,
    referrer_code: str | None = None,
    user_agent: str = "pytest-agent",
    device_fingerprint: str | None = None,
    ip: str = "10.10.10.10",
):
    headers = {
        "user-agent": user_agent,
        "x-forwarded-for": ip,
    }
    send_resp = client.post("/api/v1/auth/send-code", json={"phone": phone}, headers=headers)
    assert send_resp.status_code == 200
    code = send_resp.json()["data"]["debug_code"]
    payload = {"phone": phone, "code": code}
    if referrer_code:
        payload["referrer_code"] = referrer_code
    if device_fingerprint:
        payload["device_fingerprint"] = device_fingerprint
    return client.post("/api/v1/auth/login", json=payload, headers=headers)


def _prepare_referral_rules(db_session: Session, ip_limit_24h: int) -> None:
    db_session.add(
        SystemConfig(
            category="referral",
            config_key="rules",
            config_value={
                "register_inviter_credits": 500,
                "register_invitee_bonus": 500,
                "first_pay_ratio": 0.1,
                "recurring_ratio": 0.05,
                "ip_limit_24h": ip_limit_24h,
            },
        )
    )
    db_session.commit()


def _prepare_inviter(db_session: Session, phone: str, invite_code: str) -> None:
    inviter = User(phone=phone, nickname="inviter", credits=0)
    db_session.add(inviter)
    db_session.flush()
    db_session.add(UserInviteCode(user_id=inviter.id, invite_code=invite_code))
    db_session.commit()


def test_banned_user_login_records_risk_log(client: TestClient, db_session: Session) -> None:
    banned_user = User(phone="13800001234", nickname="banned", credits=0, is_banned=True)
    db_session.add(banned_user)
    db_session.commit()

    resp = _login_with_code(client, phone=banned_user.phone)
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 4012

    logs = (
        db_session.query(RegistrationRiskLog)
        .filter(RegistrationRiskLog.phone == banned_user.phone)
        .order_by(RegistrationRiskLog.id.desc())
        .all()
    )
    assert logs
    assert logs[0].reason == "banned_user_login_attempt"


def test_same_ip_over_limit_will_be_logged(client: TestClient, db_session: Session, monkeypatch) -> None:
    monkeypatch.setattr(worker_tasks.grant_register_rewards_async, "delay", lambda *_args, **_kwargs: None)
    _prepare_referral_rules(db_session, ip_limit_24h=1)
    _prepare_inviter(db_session, phone="13800001001", invite_code="U9000001")

    first = _login_with_code(client, phone="13800002001", referrer_code="U9000001", user_agent="risk-ip-agent")
    assert first.status_code == 200
    assert first.json()["code"] == 0

    second = _login_with_code(client, phone="13800002002", referrer_code="U9000001", user_agent="risk-ip-agent")
    assert second.status_code == 200
    assert second.json()["code"] == 0

    logs = (
        db_session.query(RegistrationRiskLog)
        .filter(RegistrationRiskLog.phone == "13800002002")
        .order_by(RegistrationRiskLog.id.desc())
        .all()
    )
    assert logs
    reasons = {row.reason for row in logs}
    assert "same_ip_over_1_24h" in reasons


def test_same_device_over_threshold_will_be_logged(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(worker_tasks.grant_register_rewards_async, "delay", lambda *_args, **_kwargs: None)
    _prepare_referral_rules(db_session, ip_limit_24h=99)
    _prepare_inviter(db_session, phone="13800001002", invite_code="U9000002")

    for idx in range(4):
        phone = f"1380000300{idx + 1}"
        resp = _login_with_code(
            client,
            phone=phone,
            referrer_code="U9000002",
            user_agent="risk-device-agent",
            device_fingerprint="same-device-fp",
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    logs = (
        db_session.query(RegistrationRiskLog)
        .filter(RegistrationRiskLog.phone == "13800003004")
        .order_by(RegistrationRiskLog.id.desc())
        .all()
    )
    assert logs
    reasons = {row.reason for row in logs}
    assert "same_device_over_3_24h" in reasons


def test_send_code_ip_rate_limit(client: TestClient) -> None:
    from app.config import get_settings

    settings = get_settings()
    old_limit = settings.auth_send_code_ip_1h_limit
    settings.auth_send_code_ip_1h_limit = 2
    try:
        resp1 = client.post(
            "/api/v1/auth/send-code",
            json={"phone": "13800004001"},
            headers={"x-forwarded-for": "10.10.10.88"},
        )
        assert resp1.status_code == 200

        resp2 = client.post(
            "/api/v1/auth/send-code",
            json={"phone": "13800004002"},
            headers={"x-forwarded-for": "10.10.10.88"},
        )
        assert resp2.status_code == 200

        resp3 = client.post(
            "/api/v1/auth/send-code",
            json={"phone": "13800004003"},
            headers={"x-forwarded-for": "10.10.10.88"},
        )
        assert resp3.status_code == 400
        body = resp3.json()
        assert body["code"] == 4019
    finally:
        settings.auth_send_code_ip_1h_limit = old_limit


def test_login_ip_rate_limit(client: TestClient) -> None:
    from app.config import get_settings

    settings = get_settings()
    old_limit = settings.auth_login_ip_10m_limit
    settings.auth_login_ip_10m_limit = 1
    try:
        first = _login_with_code(client, phone="13800005001", ip="10.10.10.99")
        assert first.status_code == 200

        second = _login_with_code(client, phone="13800005002", ip="10.10.10.99")
        assert second.status_code == 400
        body = second.json()
        assert body["code"] == 4020
    finally:
        settings.auth_login_ip_10m_limit = old_limit


def test_new_user_login_uses_configured_initial_credits(client: TestClient, db_session: Session) -> None:
    db_session.add(
        SystemConfig(
            category="system",
            config_key="login",
            config_value={
                "debug_code_enabled": True,
                "new_user_initial_credits": 2345,
            },
        )
    )
    db_session.commit()

    resp = _login_with_code(client, phone="13800006001")
    assert resp.status_code == 200

    user_id = resp.json()["data"]["user"]["id"]
    user = db_session.get(User, user_id)
    assert user is not None
    assert user.credits == 2345
