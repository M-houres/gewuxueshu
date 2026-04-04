import io
import json
from io import BytesIO
import zipfile

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import CreditTransaction, Order, ReferralRelation, SystemConfig, Task, User, UserInviteCode
from app.services.algo_package_service import install_algorithm_package


def _build_package_zip(*, platform: str, function_type: str, name: str = "engine") -> bytes:
    manifest = {
        "name": name,
        "version": "1.0.0",
        "platform": platform,
        "function_type": function_type,
        "entry": "main.py",
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
        zf.writestr("main.py", "def process(text):\n    return {'text': str(text)}\n")
    return buf.getvalue()


def _activate_slot(db_session: Session, *, platform: str, function_type: str) -> None:
    install_algorithm_package(
        db_session,
        file_bytes=_build_package_zip(platform=platform, function_type=function_type, name=f"{function_type}_engine"),
        platform=platform,
        function_type=function_type,
        uploaded_by=1,
        activate_after_upload=True,
    )
    db_session.commit()


def test_client_source_flows_through_login_task_and_payment(
    client: TestClient,
    db_session: Session,
    monkeypatch,
    settings_override,
) -> None:
    inviter = User(phone="13800002000", nickname="inviter", source="web", credits=0)
    db_session.add(inviter)
    db_session.flush()
    db_session.add(UserInviteCode(user_id=inviter.id, invite_code="INVITE20"))
    db_session.add(
        SystemConfig(
            category="system",
            config_key="payment",
            config_value={"provider": "mock", "test_mode": True},
            updated_by=1,
        )
    )
    db_session.commit()
    _activate_slot(db_session, platform="cnki", function_type="aigc_detect")

    monkeypatch.setattr("app.worker_tasks.dispatch_background_task", lambda *_args, **_kwargs: "test")

    source_headers = {"X-Client-Source": "miniprogram"}
    send_resp = client.post("/api/v1/auth/send-code", json={"phone": "13800002001"}, headers=source_headers)
    assert send_resp.status_code == 200
    debug_code = send_resp.json()["data"]["debug_code"]

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"phone": "13800002001", "code": debug_code, "referrer_code": "INVITE20"},
        headers=source_headers,
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()["data"]
    token = login_data["token"]
    user_id = login_data["user"]["id"]
    assert login_data["user"]["source"] == "miniprogram"

    created_user = db_session.get(User, user_id)
    assert created_user is not None
    assert created_user.source == "miniprogram"

    init_tx = (
        db_session.query(CreditTransaction)
        .filter(CreditTransaction.user_id == user_id, CreditTransaction.related_id == f"user_init:{user_id}")
        .first()
    )
    assert init_tx is not None
    assert init_tx.source == "miniprogram"

    relation = db_session.query(ReferralRelation).filter(ReferralRelation.invitee_id == user_id).first()
    assert relation is not None
    assert relation.source == "miniprogram"

    auth_headers = {
        "Authorization": f"Bearer {token}",
        "X-Client-Source": "miniprogram",
    }

    mock_pay_resp = client.post(
        "/api/v1/billing/mock-pay",
        json={"package_name": "入门包"},
        headers=auth_headers,
    )
    assert mock_pay_resp.status_code == 200
    order_no = mock_pay_resp.json()["data"]["order_no"]

    order = db_session.query(Order).filter(Order.order_no == order_no).first()
    assert order is not None
    assert order.source == "miniprogram"

    package_tx = (
        db_session.query(CreditTransaction)
        .filter(CreditTransaction.user_id == user_id, CreditTransaction.related_id == order_no)
        .first()
    )
    assert package_tx is not None
    assert package_tx.source == "miniprogram"

    submit_resp = client.post(
        "/api/v1/tasks/submit",
        data={"task_type": "aigc_detect", "platform": "cnki"},
        files={"paper": ("paper.txt", BytesIO("hello论文123".encode("utf-8")), "text/plain")},
        headers=auth_headers,
    )
    assert submit_resp.status_code == 200
    task_id = submit_resp.json()["data"]["id"]

    task = db_session.get(Task, task_id)
    assert task is not None
    assert task.source == "miniprogram"

    task_tx = (
        db_session.query(CreditTransaction)
        .filter(CreditTransaction.user_id == user_id, CreditTransaction.related_id == f"task:{task_id}")
        .first()
    )
    assert task_tx is not None
    assert task_tx.source == "miniprogram"


def test_wechat_mock_authorize_supports_miniprogram_identity_fields(
    client: TestClient,
    db_session: Session,
) -> None:
    qr_resp = client.get("/api/v1/auth/wx/qrcode")
    assert qr_resp.status_code == 200
    key = qr_resp.json()["data"]["key"]

    auth_resp = client.post(
        "/api/v1/auth/wx/mock-authorize",
        json={
            "key": key,
            "scene": "miniprogram",
            "openid": "mp_openid_001",
            "unionid": "unionid_001",
        },
        headers={"X-Client-Source": "miniprogram"},
    )
    assert auth_resp.status_code == 200

    poll_resp = client.get(f"/api/v1/auth/wx/poll/{key}")
    assert poll_resp.status_code == 200
    poll_data = poll_resp.json()["data"]
    assert poll_data["status"] == "authorized"

    user = db_session.get(User, poll_data["user"]["id"])
    assert user is not None
    assert user.source == "miniprogram"
    assert user.wechat_unionid == "unionid_001"
    assert user.wechat_openid_mp == "mp_openid_001"
    assert user.wechat_openid_web in {None, ""}
    assert user.openid in {None, ""}
