from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.deps import current_admin
from app.main import app
from app.models import AdminUser
from app.security import hash_password


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


def test_list_admin_users_supports_filters_and_summary(
    client: TestClient,
    admin_override,
) -> None:
    payload_a = {
        "username": "ops_filter_a",
        "password": "Passw0rd!123",
        "permissions": ["dashboard:view", "tasks:view"],
        "is_active": True,
    }
    payload_b = {
        "username": "ops_filter_b",
        "password": "Passw0rd!123",
        "permissions": ["dashboard:view", "tasks:view"],
        "is_active": False,
    }
    assert client.post("/api/v1/admin/admin-users", json=payload_a).status_code == 200
    assert client.post("/api/v1/admin/admin-users", json=payload_b).status_code == 200

    resp = client.get(
        "/api/v1/admin/admin-users",
        params={
            "keyword": "filter_a",
            "role": "operator",
            "is_active": "true",
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["items"]) == 1
    assert data["items"][0]["username"] == "ops_filter_a"

    summary = data["summary"]
    assert summary["total"] == 2
    assert summary["active"] == 1
    assert summary["inactive"] == 1


def test_create_admin_requires_non_empty_permissions(
    client: TestClient,
    admin_override,
) -> None:
    resp = client.post(
        "/api/v1/admin/admin-users",
        json={
            "username": "ops_empty_perm",
            "password": "Passw0rd!123",
            "permissions": [],
            "is_active": True,
        },
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == 4313


def test_reset_admin_password_can_auto_generate(
    client: TestClient,
    admin_override,
) -> None:
    create_resp = client.post(
        "/api/v1/admin/admin-users",
        json={
            "username": "ops_reset_pass",
            "password": "Passw0rd!123",
            "permissions": ["dashboard:view", "tasks:view"],
            "is_active": True,
        },
    )
    assert create_resp.status_code == 200
    admin_id = create_resp.json()["data"]["admin"]["id"]

    resp = client.post(
        f"/api/v1/admin/admin-users/{admin_id}/password",
        json={"auto_generate": True},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    generated = data["generated_password"]
    assert isinstance(generated, str)
    assert len(generated) >= 12


def test_super_admin_cannot_disable_self(
    client: TestClient,
    admin_override,
    db_session,
) -> None:
    db_session.add(
        AdminUser(
            id=1,
            username="admin",
            password_hash=hash_password("Passw0rd!123"),
            role="super_admin",
            is_active=True,
            permissions_json=[],
        )
    )
    db_session.commit()

    resp = client.post(
        "/api/v1/admin/admin-users/1/status",
        json={"is_active": False},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == 4314
