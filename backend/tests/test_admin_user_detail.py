from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CreditTransaction, CreditType, Task, TaskStatus, TaskType, User


def test_admin_user_detail_returns_summary(
    client: TestClient,
    db_session: Session,
    admin_override,
) -> None:
    user = User(phone="13800009999", nickname="u1", credits=120)
    db_session.add(user)
    db_session.flush()

    db_session.add(
        CreditTransaction(
            user_id=user.id,
            tx_type=CreditType.INIT,
            delta=120,
            balance_before=0,
            balance_after=120,
            reason="init",
            related_id=f"init:{user.id}",
        )
    )
    db_session.add(
        Task(
            user_id=user.id,
            task_type=TaskType.DEDUP,
            platform="cnki",
            status=TaskStatus.COMPLETED,
            source_filename="a.docx",
            source_path="/tmp/a.docx",
            char_count=100,
            cost_credits=200,
            created_at=datetime.utcnow(),
        )
    )
    db_session.commit()

    resp = client.get(f"/api/v1/admin/users/{user.id}/detail")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["user"]["id"] == user.id
    assert isinstance(data["credit_transactions"], list)
    assert isinstance(data["tasks"], list)
    assert data["tasks"][0]["source_filename"] == "a.docx"
    assert "result_json" in data["tasks"][0]
    assert "updated_at" in data["tasks"][0]


def test_admin_user_ban_toggle(
    client: TestClient,
    db_session: Session,
    admin_override,
) -> None:
    user = User(phone="13800008888", nickname="u2", credits=0, is_banned=False)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    resp = client.post(f"/api/v1/admin/users/{user.id}/ban", json={"is_banned": True})
    assert resp.status_code == 200
    db_session.refresh(user)
    assert user.is_banned is True
