from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.deps import current_admin
from app.main import app
from app.models import SystemSwitch


def test_admin_switch_mode_and_logs(
    client: TestClient,
    db_session: Session,
    admin_override,
) -> None:
    current = client.get("/api/v1/admin/switch/current")
    assert current.status_code == 200
    assert current.json()["data"]["current_mode"] in {"LLM_PLUS_ALGO", "ALGO_ONLY"}

    change = client.post("/api/v1/admin/switch/mode", json={"mode": "ALGO_ONLY"})
    assert change.status_code == 200
    assert change.json()["data"]["current_mode"] == "ALGO_ONLY"

    switch = db_session.query(SystemSwitch).first()
    assert switch is not None
    assert switch.current_mode == "ALGO_ONLY"

    logs = client.get("/api/v1/admin/switch/logs", params={"page": 1, "page_size": 20})
    assert logs.status_code == 200
    items = logs.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["to_mode"] == "ALGO_ONLY"


def test_admin_switch_mode_forbidden_for_operator(
    client: TestClient,
) -> None:
    app.dependency_overrides[current_admin] = lambda: SimpleNamespace(id=2, username="op", role="operator")
    try:
        resp = client.post("/api/v1/admin/switch/mode", json={"mode": "ALGO_ONLY"})
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.pop(current_admin, None)
