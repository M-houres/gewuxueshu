from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AdminUser


def test_config_audit_logs_include_changed_fields(
    client: TestClient,
    db_session: Session,
    admin_override,
) -> None:
    db_session.add(AdminUser(id=1, username="admin", password_hash="x", role="super_admin"))
    db_session.commit()

    resp = client.post(
        "/api/v1/admin/configs/billing",
        json={"aigc_rate": 1, "dedup_rate": 6, "rewrite_rate": 2},
    )
    assert resp.status_code == 200

    logs = client.get("/api/v1/admin/configs/audit-logs", params={"page": 1, "page_size": 10})
    assert logs.status_code == 200

    items = logs.json()["data"]["items"]
    assert len(items) >= 1

    first = items[0]
    assert first["admin_username"] == "admin"
    assert first["target_type"] == "billing"
    assert first["target_type_label"] == "计费规则"
    assert first["changed_fields"] == ["dedup_rate"]
    assert first["changed_field_labels"] == ["降重单价"]
    assert first["changed_count"] == 1
    assert "计费规则" in first["summary"]

    readiness = client.get("/api/v1/admin/configs/readiness")
    assert readiness.status_code == 200
    assert len(readiness.json()["data"]["items"]) == 5
