from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.deps import current_user
from app.main import app
from app.models import User


def test_invite_code_api_returns_qrcode_data_url(client: TestClient, db_session: Session) -> None:
    user = User(phone="13800009992", nickname="invite-user", credits=0)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    app.dependency_overrides[current_user] = lambda: user
    try:
        resp = client.get("/api/v1/users/me/invite-code")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["invite_code"]
        assert data["invite_link"]
        assert data["qrcode_data_url"].startswith("data:image/png;base64,")
    finally:
        app.dependency_overrides.pop(current_user, None)
