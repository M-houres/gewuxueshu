import io
import json
import zipfile
from io import BytesIO

from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.deps import current_user
from app.main import app
from app.models import SystemConfig, Task, TaskStatus, TaskType, User
from app.services.algo_package_service import install_algorithm_package
from app.services.process_strategy_service import get_process_strategy


def _make_docx_bytes(text: str) -> BytesIO:
    doc = Document()
    doc.add_paragraph(text)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


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
        zf.writestr("main.py", "def process(text):\n    return str(text)\n")
    return buf.getvalue()


def test_admin_strategies_list_default_nine_cells(
    client: TestClient,
    admin_override,
) -> None:
    resp = client.get("/api/v1/admin/strategies")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0

    data = body["data"]
    items = data["items"]
    assert len(items) == 9
    assert set(data["platforms"]) == {"cnki", "vip", "paperpass"}
    assert set(data["task_types"]) == {"aigc_detect", "dedup", "rewrite"}

    for row in items:
        assert row["process_mode"] == "algo_only"
        assert row["is_enabled"] is True
        assert row["timeout_sec"] == 300


def test_admin_enable_strategy_requires_active_package(
    client: TestClient,
    admin_override,
) -> None:
    fail_resp = client.put(
        "/api/v1/admin/strategies/rewrite/cnki",
        json={"is_enabled": True},
    )
    assert fail_resp.status_code == 400
    fail_body = fail_resp.json()
    assert fail_body["code"] == 4118


def test_admin_enable_strategy_success_after_active_package(
    client: TestClient,
    db_session: Session,
    admin_override,
    settings_override,
) -> None:
    install_algorithm_package(
        db_session,
        file_bytes=_build_package_zip(platform="cnki", function_type="rewrite", name="rewrite_engine"),
        platform="cnki",
        function_type="rewrite",
        uploaded_by=1,
        activate_after_upload=True,
    )
    db_session.commit()

    resp = client.put(
        "/api/v1/admin/strategies/rewrite/cnki",
        json={
            "is_enabled": True,
            "process_mode": "algo_llm",
            "timeout_sec": 600,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["process_mode"] == "algo_llm"
    assert body["data"]["is_enabled"] is True
    assert body["data"]["timeout_sec"] == 600
    assert body["data"]["active_package"]["name"] == "rewrite_engine"


def test_task_submit_requires_active_package_for_enabled_strategy(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    user = User(phone="13800008881", nickname="strategy-user", credits=10000)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    monkeypatch.setattr("app.worker_tasks.process_task_async.delay", lambda *_args, **_kwargs: None)
    app.dependency_overrides[current_user] = lambda: user
    try:
        file_bytes = _make_docx_bytes("abcdefghij")
        resp = client.post(
            "/api/v1/tasks/submit",
            data={"task_type": "dedup", "platform": "cnki"},
            files={"paper": ("sample.docx", file_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["code"] == 4118
    finally:
        app.dependency_overrides.pop(current_user, None)


def test_user_task_result_hides_processing_mode_fields(
    client: TestClient,
    db_session: Session,
) -> None:
    user = User(phone="13800008882", nickname="hide-mode-user", credits=10000)
    db_session.add(user)
    db_session.flush()

    task = Task(
        user_id=user.id,
        task_type=TaskType.AIGC_DETECT,
        platform="cnki",
        processing_mode="LLM_PLUS_ALGO",
        source="web",
        status=TaskStatus.COMPLETED,
        source_filename="paper.docx",
        source_path="/tmp/paper.docx",
        output_path="/tmp/out.pdf",
        char_count=10,
        cost_credits=10,
        result_json={
            "ai_score": 0.3,
            "mode": "LLM_PLUS_ALGO",
            "llm_used": True,
            "algo_package_used": True,
            "score_breakdown": {
                "base_score": 0.2,
                "llm_score": 0.6,
                "algo_package_score": 0.4,
                "pipeline_mode": "llm_plus_algo",
            },
        },
    )
    db_session.add(task)
    db_session.commit()

    app.dependency_overrides[current_user] = lambda: user
    try:
        list_resp = client.get("/api/v1/tasks/my")
        assert list_resp.status_code == 200
        list_item = list_resp.json()["data"]["items"][0]
        result = list_item["result_json"]
        assert "mode" not in result
        assert "processing_mode" not in result
        assert "llm_used" not in result
        assert "algo_package_used" not in result
        assert "llm_score" not in result.get("score_breakdown", {})
        assert "algo_package_score" not in result.get("score_breakdown", {})
        assert "pipeline_mode" not in result.get("score_breakdown", {})

        detail_resp = client.get(f"/api/v1/tasks/{task.id}")
        assert detail_resp.status_code == 200
        detail_result = detail_resp.json()["data"]["result_json"]
        assert "mode" not in detail_result
        assert "llm_used" not in detail_result
        assert "algo_package_used" not in detail_result
    finally:
        app.dependency_overrides.pop(current_user, None)


def test_strategy_string_false_is_parsed_as_disabled(db_session: Session) -> None:
    db_session.add(
        SystemConfig(
            category="process_strategies_v1",
            config_key="rewrite:cnki",
            config_value={"process_mode": "algo_only", "is_enabled": "false", "timeout_sec": 300},
            updated_by=1,
        )
    )
    db_session.commit()

    strategy = get_process_strategy(db_session, task_type=TaskType.REWRITE, platform="cnki")
    assert strategy["is_enabled"] is False
