from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_wx_qrcode_poll_and_mock_authorize(
    client: TestClient,
    db_session: Session,
) -> None:
    qr_resp = client.get("/api/v1/auth/wx/qrcode")
    assert qr_resp.status_code == 200
    qr_data = qr_resp.json()["data"]
    assert qr_data["key"]
    assert qr_data["qrcode_data_url"].startswith("data:image/png;base64,")

    auth_resp = client.post("/api/v1/auth/wx/mock-authorize", json={"key": qr_data["key"]})
    assert auth_resp.status_code == 200

    poll_resp = client.get(f"/api/v1/auth/wx/poll/{qr_data['key']}")
    assert poll_resp.status_code == 200
    poll_data = poll_resp.json()["data"]
    assert poll_data["status"] == "authorized"
    assert poll_data["token"]
    assert poll_data["user"]["id"] >= 1
