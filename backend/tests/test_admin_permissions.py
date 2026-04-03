from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.deps import current_admin
from app.main import app


def test_super_admin_can_create_admin_and_assign_permissions(
    client: TestClient,
    admin_override,
) -> None:
    resp = client.post(
        "/api/v1/admin/admin-users",
        json={
            "username": "ops_user_1",
            "password": "Passw0rd!123",
            "permissions": ["dashboard:view", "tasks:view", "orders:view"],
            "is_active": True,
        },
    )
    assert resp.status_code == 200
    admin = resp.json()["data"]["admin"]
    assert admin["username"] == "ops_user_1"
    assert admin["role"] == "operator"
    assert admin["permissions"] == ["dashboard:view", "orders:view", "tasks:view"]

    list_resp = client.get("/api/v1/admin/admin-users")
    assert list_resp.status_code == 200
    rows = list_resp.json()["data"]["items"]
    matched = [row for row in rows if row["username"] == "ops_user_1"]
    assert len(matched) == 1
    assert matched[0]["is_active"] is True


def test_permission_guard_blocks_ungranted_admin_endpoints(
    client: TestClient,
) -> None:
    app.dependency_overrides[current_admin] = lambda: SimpleNamespace(
        id=2,
        username="operator",
        role="operator",
        is_active=True,
        permissions_json=["tasks:view"],
    )
    try:
        denied = client.get("/api/v1/admin/users")
        assert denied.status_code == 403

        allowed = client.get("/api/v1/admin/tasks")
        assert allowed.status_code == 200
    finally:
        app.dependency_overrides.pop(current_admin, None)
