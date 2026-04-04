import io
import json
import os
import zipfile

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.algo_package_service import install_algorithm_package, run_active_package, run_package_smoke_test


def _build_package_zip(
    manifest: dict,
    entry_content: str = "def process(text):\n    return str(text).replace('样例', '测试')\n",
) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
        if manifest.get("entry") != "main.py":
            zf.writestr("main.py", "def process(text):\n    return str(text).replace('样例', '测试')\n")
        zf.writestr(manifest["entry"], entry_content)
    return buf.getvalue()


def test_admin_upload_algorithm_package_success(
    client: TestClient,
    admin_override,
    settings_override,
) -> None:
    manifest = {
        "name": "dedup_engine",
        "version": "1.0.0",
        "platform": "cnki",
        "function_type": "dedup",
        "entry": "main.py",
    }
    file_bytes = _build_package_zip(manifest)

    resp = client.post(
        "/api/v1/admin/algo-packages/upload",
        data={"activate": "true", "platform": "cnki", "function_type": "dedup"},
        files={"file": ("dedup_engine.zip", file_bytes, "application/zip")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["name"] == "dedup_engine"
    assert body["data"]["active_slot"]["version"] == "1.0.0"
    assert body["data"]["smoke_status"] == "passed"

    list_resp = client.get("/api/v1/admin/algo-packages")
    assert list_resp.status_code == 200
    items = list_resp.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["name"] == "dedup_engine"
    assert items[0]["version"] == "1.0.0"
    assert items[0]["platform"] == "cnki"
    assert items[0]["function_type"] == "dedup"
    assert items[0]["active"] is True


def test_admin_upload_algorithm_package_manifest_smoke_fail(
    client: TestClient,
    admin_override,
    settings_override,
) -> None:
    manifest = {
        "name": "detect_engine",
        "version": "1.0.0",
        "platform": "cnki",
        "function_type": "aigc_detect",
        "entry": "engine/missing.py",
    }
    # omit declared entry file, simulate smoke test failure
    bad_buf = io.BytesIO()
    with zipfile.ZipFile(bad_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
        zf.writestr("main.py", "def process(text):\n    return text\n")
        zf.writestr("engine/another.py", "print('x')")

    resp = client.post(
        "/api/v1/admin/algo-packages/upload",
        data={"activate": "true", "platform": "cnki", "function_type": "aigc_detect"},
        files={"file": ("detect_engine.zip", bad_buf.getvalue(), "application/zip")},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 4507


def test_run_package_smoke_test_uses_manifest_entry(
    settings_override,
) -> None:
    manifest = {
        "name": "rewrite_engine",
        "version": "1.0.0",
        "platform": "cnki",
        "function_type": "rewrite",
        "entry": "engine/custom.py",
    }
    file_bytes = _build_package_zip(
        manifest,
        entry_content="def process(text):\n    return 'ENTRY_FILE'\n",
    )

    smoke = run_package_smoke_test(file_bytes)
    assert smoke["status"] == "passed"
    assert smoke["preview"] == "ENTRY_FILE"


def test_run_active_package_uses_manifest_entry(
    db_session: Session,
    settings_override,
) -> None:
    manifest = {
        "name": "rewrite_engine",
        "version": "1.0.0",
        "platform": "cnki",
        "function_type": "rewrite",
        "entry": "engine/custom.py",
    }
    file_bytes = _build_package_zip(
        manifest,
        entry_content="def process(text):\n    return 'ENTRY_FILE'\n",
    )

    result = install_algorithm_package(
        db_session,
        file_bytes=file_bytes,
        platform="cnki",
        function_type="rewrite",
        uploaded_by=1,
        activate_after_upload=True,
    )
    assert result["active_slot"]["entry"] == "engine/custom.py"

    active_result = run_active_package(
        db_session,
        platform="cnki",
        function_type="rewrite",
        text="input",
    )
    assert active_result is not None
    output, active = active_result
    assert output == "ENTRY_FILE"
    assert active["entry"] == "engine/custom.py"


def test_admin_upload_algorithm_package_custom_entry_without_main_py_success(
    client: TestClient,
    admin_override,
    settings_override,
) -> None:
    manifest = {
        "name": "rewrite_engine_zip_only",
        "version": "1.0.0",
        "platform": "cnki",
        "function_type": "rewrite",
        "entry": "engine/custom.py",
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
        zf.writestr("engine/custom.py", "def process(text):\n    return 'ZIP_ONLY_ENTRY'\n")

    resp = client.post(
        "/api/v1/admin/algo-packages/upload",
        data={"activate": "true", "platform": "cnki", "function_type": "rewrite"},
        files={"file": ("rewrite_engine_zip_only.zip", buf.getvalue(), "application/zip")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["entry"] == "engine/custom.py"
    assert body["data"]["active_slot"]["entry"] == "engine/custom.py"


def test_run_active_package_executes_in_subprocess(
    db_session: Session,
    settings_override,
) -> None:
    manifest = {
        "name": "pid_engine",
        "version": "1.0.0",
        "platform": "cnki",
        "function_type": "dedup",
        "entry": "main.py",
    }
    file_bytes = _build_package_zip(
        manifest,
        entry_content="import os\n\ndef process(text):\n    return {'pid': os.getpid(), 'text': str(text)}\n",
    )

    install_algorithm_package(
        db_session,
        file_bytes=file_bytes,
        platform="cnki",
        function_type="dedup",
        uploaded_by=1,
        activate_after_upload=True,
    )

    active_result = run_active_package(
        db_session,
        platform="cnki",
        function_type="dedup",
        text="input",
    )
    assert active_result is not None
    output, _active = active_result
    assert output["text"] == "input"
    assert int(output["pid"]) != os.getpid()


def test_run_active_package_supports_keyword_only_process_signature(
    db_session: Session,
    settings_override,
) -> None:
    manifest = {
        "name": "kw_engine",
        "version": "1.0.0",
        "platform": "cnki",
        "function_type": "rewrite",
        "entry": "main.py",
    }
    file_bytes = _build_package_zip(
        manifest,
        entry_content="def process(*, input_text):\n    return {'text': str(input_text) + '::ok'}\n",
    )

    install_algorithm_package(
        db_session,
        file_bytes=file_bytes,
        platform="cnki",
        function_type="rewrite",
        uploaded_by=1,
        activate_after_upload=True,
    )

    active_result = run_active_package(
        db_session,
        platform="cnki",
        function_type="rewrite",
        text="payload",
    )
    assert active_result is not None
    output, _active = active_result
    assert output["text"] == "payload::ok"


def test_run_active_package_ignores_package_stdout_noise(
    db_session: Session,
    settings_override,
) -> None:
    manifest = {
        "name": "print_engine",
        "version": "1.0.0",
        "platform": "cnki",
        "function_type": "dedup",
        "entry": "main.py",
    }
    file_bytes = _build_package_zip(
        manifest,
        entry_content="def process(text):\n    print('debug line from package')\n    return {'text': str(text)}\n",
    )

    install_algorithm_package(
        db_session,
        file_bytes=file_bytes,
        platform="cnki",
        function_type="dedup",
        uploaded_by=1,
        activate_after_upload=True,
    )

    active_result = run_active_package(
        db_session,
        platform="cnki",
        function_type="dedup",
        text="input",
    )
    assert active_result is not None
    output, _active = active_result
    assert output["text"] == "input"


def test_admin_download_algorithm_package_guide(
    client: TestClient,
    admin_override,
    settings_override,
) -> None:
    resp = client.get("/api/v1/admin/algo-packages/guide")
    assert resp.status_code == 200
    assert "application/octet-stream" in (resp.headers.get("content-type") or "")
    disposition = resp.headers.get("content-disposition") or ""
    assert "ALGO_PACKAGE_AUTHORING_GUIDE.md" in disposition
    assert "manifest.json".encode("utf-8") in resp.content
    assert "process".encode("utf-8") in resp.content

    legacy_resp = client.get("/api/v1/admin/algo-package-guide")
    assert legacy_resp.status_code == 200


def test_admin_download_algorithm_package_authoring_bundle(
    client: TestClient,
    admin_override,
    settings_override,
) -> None:
    resp = client.get("/api/v1/admin/algo-packages/authoring-bundle")
    assert resp.status_code == 200
    assert "application/zip" in (resp.headers.get("content-type") or "")
    disposition = resp.headers.get("content-disposition") or ""
    assert "ALGO_PACKAGE_AUTHORING_SPEC_BUNDLE.zip" in disposition

    with zipfile.ZipFile(io.BytesIO(resp.content), "r") as zf:
        names = set(zf.namelist())
        readme = zf.read("README.md").decode("utf-8")
        runtime_doc = zf.read("docs/00_runtime_contract.md").decode("utf-8")
        blank_manifest = json.loads(zf.read("blank_packages/cnki/dedup/manifest.json").decode("utf-8"))
        blank_main = zf.read("blank_packages/paperpass/rewrite/main.py").decode("utf-8")

    assert "docs/01_aigc_detect_spec.md" in names
    assert "docs/02_dedup_spec.md" in names
    assert "docs/03_rewrite_spec.md" in names
    assert "blank_packages/vip/aigc_detect/main.py" in names
    assert "blank_packages/paperpass/rewrite/README.md" in names
    assert "真实运行契约" in readme
    assert "smoke test" in runtime_doc
    assert blank_manifest["platform"] == "cnki"
    assert blank_manifest["function_type"] == "dedup"
    assert "def process" in blank_main


def test_admin_download_algorithm_package_template(
    client: TestClient,
    admin_override,
    settings_override,
) -> None:
    resp = client.get(
        "/api/v1/admin/algo-packages/template",
        params={"platform": "paperpass", "function_type": "rewrite"},
    )
    assert resp.status_code == 200
    assert "application/zip" in (resp.headers.get("content-type") or "")
    disposition = resp.headers.get("content-disposition") or ""
    assert "algo_package_template_paperpass_rewrite" in disposition

    with zipfile.ZipFile(io.BytesIO(resp.content), "r") as zf:
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        readme = zf.read("README.md").decode("utf-8")

    assert manifest["platform"] == "paperpass"
    assert manifest["function_type"] == "rewrite"
    assert manifest["entry"] == "main.py"
    assert "当前机器的 Python" not in readme
    assert "process" in readme


def test_admin_download_uploaded_algorithm_package(
    client: TestClient,
    admin_override,
    settings_override,
) -> None:
    manifest = {
        "name": "downloadable_engine",
        "version": "1.0.0",
        "platform": "cnki",
        "function_type": "dedup",
        "entry": "main.py",
    }
    file_bytes = _build_package_zip(manifest)

    upload_resp = client.post(
        "/api/v1/admin/algo-packages/upload",
        data={"activate": "true", "platform": "cnki", "function_type": "dedup"},
        files={"file": ("downloadable_engine.zip", file_bytes, "application/zip")},
    )
    assert upload_resp.status_code == 200

    resp = client.get(
        "/api/v1/admin/algo-packages/download",
        params={"platform": "cnki", "function_type": "dedup", "version": "1.0.0"},
    )
    assert resp.status_code == 200
    assert "application/zip" in (resp.headers.get("content-type") or "")
    disposition = resp.headers.get("content-disposition") or ""
    assert "algo_package_cnki_dedup_1.0.0.zip" in disposition

    with zipfile.ZipFile(io.BytesIO(resp.content), "r") as zf:
        manifest_payload = json.loads(zf.read("manifest.json").decode("utf-8"))
    assert manifest_payload["name"] == "downloadable_engine"


def test_admin_deactivate_algorithm_package(
    client: TestClient,
    admin_override,
    settings_override,
) -> None:
    manifest = {
        "name": "toggle_engine",
        "version": "1.0.0",
        "platform": "vip",
        "function_type": "rewrite",
        "entry": "main.py",
    }
    file_bytes = _build_package_zip(manifest)

    upload_resp = client.post(
        "/api/v1/admin/algo-packages/upload",
        data={"activate": "true", "platform": "vip", "function_type": "rewrite"},
        files={"file": ("toggle_engine.zip", file_bytes, "application/zip")},
    )
    assert upload_resp.status_code == 200

    deactivate_resp = client.post(
        "/api/v1/admin/algo-packages/deactivate",
        json={"platform": "vip", "function_type": "rewrite"},
    )
    assert deactivate_resp.status_code == 200
    body = deactivate_resp.json()
    assert body["code"] == 0
    assert body["data"]["active"] is False

    list_resp = client.get("/api/v1/admin/algo-packages")
    assert list_resp.status_code == 200
    payload = list_resp.json()["data"]
    slot = next(item for item in payload["slots"] if item["platform"] == "vip" and item["function_type"] == "rewrite")
    row = next(item for item in payload["items"] if item["platform"] == "vip" and item["function_type"] == "rewrite")
    assert slot["active_version"] is None
    assert row["active"] is False


def test_admin_bootstrap_builtin_algorithm_packages(
    client: TestClient,
    admin_override,
    settings_override,
) -> None:
    resp = client.post("/api/v1/admin/algo-packages/bootstrap")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["count"] == 9
    items = body["data"]["items"]
    assert any(item["platform"] == "cnki" and item["function_type"] == "aigc_detect" for item in items)
    assert any(item["platform"] == "vip" and item["function_type"] == "rewrite" for item in items)
    assert any(item["platform"] == "paperpass" and item["function_type"] == "dedup" for item in items)

    list_resp = client.get("/api/v1/admin/algo-packages")
    assert list_resp.status_code == 200
    rows = list_resp.json()["data"]["items"]
    assert any(row["platform"] == "cnki" and row["function_type"] == "dedup" for row in rows)
    assert any(row["platform"] == "vip" and row["function_type"] == "aigc_detect" for row in rows)
    assert any(row["platform"] == "paperpass" and row["function_type"] == "rewrite" for row in rows)
