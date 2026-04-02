import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
import traceback
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.config import get_settings
from app.exceptions import BizError
from app.models import SystemConfig, TaskType

settings = get_settings()

SUPPORTED_PLATFORMS = ("cnki", "vip", "paperpass")
SUPPORTED_FUNCTION_TYPES = tuple(t.value for t in TaskType)
ACTIVE_CATEGORY = "algo_package_slot_active"

_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{2,64}$")
_VERSION_PATTERN = re.compile(r"^[0-9]+(?:\.[0-9]+){2}(?:[-+._A-Za-z0-9]*)?$")


def make_slot_key(platform: str, function_type: str) -> str:
    return f"{platform.strip().lower()}:{function_type.strip().lower()}"


def _normalize_zip_path(raw_path: str) -> str:
    normalized = raw_path.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise BizError(code=4503, message="压缩包存在非法路径")
    return str(path)


def _validate_slot(platform: str, function_type: str) -> tuple[str, str]:
    normalized_platform = platform.strip().lower()
    normalized_function_type = function_type.strip().lower()
    if normalized_platform not in SUPPORTED_PLATFORMS:
        raise BizError(code=4522, message=f"不支持的平台:{normalized_platform}")
    if normalized_function_type not in SUPPORTED_FUNCTION_TYPES:
        raise BizError(code=4523, message=f"不支持的功能类型:{normalized_function_type}")
    return normalized_platform, normalized_function_type


def _read_manifest_from_zip(zf: zipfile.ZipFile) -> dict:
    try:
        raw_manifest = zf.read("manifest.json").decode("utf-8")
        data = json.loads(raw_manifest)
    except KeyError as exc:
        raise BizError(code=4510, message="缺少 manifest.json") from exc
    except UnicodeDecodeError as exc:
        raise BizError(code=4511, message="manifest.json 编码必须为 UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise BizError(code=4512, message="manifest.json 不是合法 JSON") from exc
    if not isinstance(data, dict):
        raise BizError(code=4514, message="manifest.json 顶层必须为对象")
    return data


def _validate_manifest(data: dict, zip_members: set[str], *, target_platform: str, target_function_type: str) -> dict:
    name = str(data.get("name", "")).strip()
    version = str(data.get("version", "")).strip()
    platform = str(data.get("platform", "")).strip().lower()
    function_type = str(data.get("function_type", "")).strip().lower()

    if not _NAME_PATTERN.fullmatch(name):
        raise BizError(code=4504, message="manifest.name 不合法")
    if not _VERSION_PATTERN.fullmatch(version):
        raise BizError(code=4505, message="manifest.version 不合法")
    if platform != target_platform:
        raise BizError(code=4524, message="manifest.platform 与上传目标槽位不匹配")
    if function_type != target_function_type:
        raise BizError(code=4525, message="manifest.function_type 与上传目标槽位不匹配")
    entry = str(data.get("entry", "main.py")).strip() or "main.py"
    normalized_entry = _normalize_zip_path(entry)
    if normalized_entry not in zip_members:
        raise BizError(code=4507, message="manifest.entry 文件不存在")

    return {
        "name": name,
        "version": version,
        "platform": platform,
        "function_type": function_type,
        "entry": normalized_entry,
    }


def _resolve_entry_path(file_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zf:
            members = {
                _normalize_zip_path(name)
                for name in zf.namelist()
                if name and not name.endswith("/")
            }
            manifest_data = _read_manifest_from_zip(zf)
    except zipfile.BadZipFile as exc:
        raise BizError(code=4513, message="上传文件不是有效 zip") from exc

    entry = str(manifest_data.get("entry", "main.py")).strip() or "main.py"
    normalized_entry = _normalize_zip_path(entry)
    if normalized_entry not in members:
        raise BizError(code=4507, message="manifest.entry 文件不存在")
    return normalized_entry


def _load_process_function(file_bytes: bytes, *, entry_path: str | None = None) -> Callable[[Any], Any]:
    target_entry = _normalize_zip_path(entry_path) if entry_path else _resolve_entry_path(file_bytes)
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zf:
            code = zf.read(target_entry).decode("utf-8")
    except KeyError as exc:
        raise BizError(code=4507, message="manifest.entry 文件不存在") from exc
    except zipfile.BadZipFile as exc:
        raise BizError(code=4513, message="上传文件不是有效 zip") from exc
    except UnicodeDecodeError as exc:
        raise BizError(code=4527, message=f"{target_entry} 编码必须为 UTF-8") from exc

    namespace: dict[str, Any] = {"__name__": "__algo_package__", "__file__": target_entry}
    try:
        exec(compile(code, target_entry, "exec"), namespace)
    except Exception as exc:
        raise BizError(code=4528, message=f"{target_entry} 加载失败: {exc}") from exc

    process_fn = namespace.get("process")
    if not callable(process_fn):
        raise BizError(code=4529, message=f"{target_entry} 必须定义可调用的 process 函数")
    return process_fn


def _algo_package_runner_cwd() -> str:
    return str(Path(__file__).resolve().parents[2])


def _run_package_in_subprocess(
    package_path: Path,
    *,
    entry_path: str,
    payload: Any,
    fallback_payload: Any | None = None,
) -> Any:
    request_payload: dict[str, Any] = {"payload": payload}
    if fallback_payload is not None:
        request_payload["fallback_payload"] = fallback_payload

    try:
        completed = subprocess.run(
            [sys.executable, "-m", "app.services.algo_package_runner", str(package_path), entry_path],
            input=json.dumps(request_payload),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=settings.algorithm_package_exec_timeout_seconds,
            cwd=_algo_package_runner_cwd(),
        )
    except subprocess.TimeoutExpired as exc:
        raise BizError(
            code=4533,
            message=f"算法包执行超时({settings.algorithm_package_exec_timeout_seconds}s)",
        ) from exc
    except OSError as exc:
        raise BizError(code=4534, message=f"算法包执行器启动失败: {exc}") from exc

    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    response = None
    if stdout:
        try:
            response = json.loads(stdout)
        except json.JSONDecodeError:
            response = None

    if completed.returncode != 0:
        if isinstance(response, dict) and response.get("error"):
            raise RuntimeError(str(response.get("error")))
        raise RuntimeError(stderr or stdout or f"算法包执行器退出码 {completed.returncode}")

    if not isinstance(response, dict):
        raise RuntimeError("算法包执行器返回了无效结果")
    if not response.get("ok"):
        raise RuntimeError(str(response.get("error") or "算法包执行失败"))
    return response.get("result")


def _run_package_bytes_in_subprocess(
    file_bytes: bytes,
    *,
    entry_path: str,
    payload: Any,
    fallback_payload: Any | None = None,
) -> Any:
    runtime_dir = settings.algorithm_package_dir / ".runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False, dir=runtime_dir) as temp_file:
        temp_file.write(file_bytes)
        package_path = Path(temp_file.name)
    try:
        return _run_package_in_subprocess(
            package_path,
            entry_path=entry_path,
            payload=payload,
            fallback_payload=fallback_payload,
        )
    finally:
        package_path.unlink(missing_ok=True)


def run_package_smoke_test(file_bytes: bytes, *, entry_path: str | None = None) -> dict:
    target_entry = _normalize_zip_path(entry_path) if entry_path else _resolve_entry_path(file_bytes)
    sample = "这是用于算法包 smoke test 的样例文本。"
    try:
        output = _run_package_bytes_in_subprocess(
            file_bytes,
            entry_path=target_entry,
            payload=sample,
            fallback_payload={"text": sample},
        )
        if output is None:
            raise BizError(code=4530, message="process 返回值不能为空")
        return {"status": "passed", "message": "smoke test passed", "preview": str(output)[:120]}
    except BizError:
        raise
    except Exception as exc:
        raise BizError(code=4531, message=f"smoke test 失败: {exc}") from exc


def validate_algorithm_package(file_bytes: bytes, *, target_platform: str, target_function_type: str) -> dict:
    if not file_bytes:
        raise BizError(code=4501, message="算法包文件为空")
    max_bytes = settings.algorithm_package_max_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise BizError(code=4502, message=f"算法包大小超过{settings.algorithm_package_max_mb}MB")

    platform, function_type = _validate_slot(target_platform, target_function_type)
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zf:
            members = {
                _normalize_zip_path(name)
                for name in zf.namelist()
                if name and not name.endswith("/")
            }
            manifest_data = _read_manifest_from_zip(zf)
    except zipfile.BadZipFile as exc:
        raise BizError(code=4513, message="上传文件不是有效 zip") from exc

    manifest = _validate_manifest(
        manifest_data,
        members,
        target_platform=platform,
        target_function_type=function_type,
    )
    return manifest


def _slot_version_dir(platform: str, function_type: str, version: str) -> Path:
    return settings.algorithm_package_dir / platform / function_type / version


def _read_manifest_from_dir(platform: str, function_type: str, version: str) -> dict:
    manifest_path = _slot_version_dir(platform, function_type, version) / "manifest.json"
    if not manifest_path.exists():
        raise BizError(code=4515, message="算法包不存在")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BizError(code=4516, message="算法包 manifest 文件损坏") from exc
    if not isinstance(data, dict):
        raise BizError(code=4517, message="算法包 manifest 文件格式错误")
    return data


def _read_meta_from_dir(platform: str, function_type: str, version: str) -> dict:
    meta_path = _slot_version_dir(platform, function_type, version) / "meta.json"
    if not meta_path.exists():
        return {}
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _upsert_active_slot(
    db: Session,
    *,
    platform: str,
    function_type: str,
    value: dict,
    updated_by: int,
) -> None:
    slot_key = make_slot_key(platform, function_type)
    row = (
        db.query(SystemConfig)
        .filter(SystemConfig.category == ACTIVE_CATEGORY, SystemConfig.config_key == slot_key)
        .first()
    )
    if row is None:
        db.add(
            SystemConfig(
                category=ACTIVE_CATEGORY,
                config_key=slot_key,
                config_value=value,
                updated_by=updated_by,
            )
        )
    else:
        row.config_value = value
        row.updated_by = updated_by


def install_algorithm_package(
    db: Session,
    *,
    file_bytes: bytes,
    platform: str,
    function_type: str,
    uploaded_by: int,
    activate_after_upload: bool = True,
) -> dict:
    normalized_platform, normalized_function_type = _validate_slot(platform, function_type)
    manifest = validate_algorithm_package(
        file_bytes,
        target_platform=normalized_platform,
        target_function_type=normalized_function_type,
    )
    smoke = run_package_smoke_test(file_bytes, entry_path=manifest["entry"])
    checksum = hashlib.sha256(file_bytes).hexdigest()
    uploaded_at = datetime.utcnow().isoformat()

    version_dir = _slot_version_dir(normalized_platform, normalized_function_type, manifest["version"])
    version_dir.mkdir(parents=True, exist_ok=True)

    package_path = version_dir / "package.zip"
    manifest_path = version_dir / "manifest.json"
    meta_path = version_dir / "meta.json"

    package_path.write_bytes(file_bytes)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    meta = {
        "name": manifest["name"],
        "version": manifest["version"],
        "platform": normalized_platform,
        "function_type": normalized_function_type,
        "entry": manifest["entry"],
        "size_bytes": len(file_bytes),
        "sha256": checksum,
        "uploaded_by": uploaded_by,
        "uploaded_at": uploaded_at,
        "smoke_status": smoke["status"],
        "smoke_message": smoke["message"],
        "smoke_preview": smoke["preview"],
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    active_slot = None
    if activate_after_upload:
        active_slot = activate_algorithm_package(
            db,
            platform=normalized_platform,
            function_type=normalized_function_type,
            version=manifest["version"],
            updated_by=uploaded_by,
        )

    return {
        "name": manifest["name"],
        "version": manifest["version"],
        "platform": normalized_platform,
        "function_type": normalized_function_type,
        "entry": manifest["entry"],
        "size_bytes": len(file_bytes),
        "sha256": checksum,
        "smoke_status": smoke["status"],
        "smoke_message": smoke["message"],
        "package_path": str(package_path),
        "active_slot": active_slot,
    }


def activate_algorithm_package(
    db: Session,
    *,
    platform: str,
    function_type: str,
    version: str,
    updated_by: int,
) -> dict:
    normalized_platform, normalized_function_type = _validate_slot(platform, function_type)
    manifest = _read_manifest_from_dir(normalized_platform, normalized_function_type, version)
    meta = _read_meta_from_dir(normalized_platform, normalized_function_type, version)

    value = {
        "name": manifest.get("name"),
        "platform": normalized_platform,
        "function_type": normalized_function_type,
        "version": version,
        "entry": manifest.get("entry", "main.py"),
        "smoke_status": meta.get("smoke_status", "unknown"),
        "uploaded_at": meta.get("uploaded_at"),
        "updated_at": datetime.utcnow().isoformat(),
    }
    _upsert_active_slot(
        db,
        platform=normalized_platform,
        function_type=normalized_function_type,
        value=value,
        updated_by=updated_by,
    )
    db.flush()
    return value


def deactivate_algorithm_package(
    db: Session,
    *,
    platform: str,
    function_type: str,
    updated_by: int,
) -> dict:
    normalized_platform, normalized_function_type = _validate_slot(platform, function_type)
    slot_key = make_slot_key(normalized_platform, normalized_function_type)
    row = (
        db.query(SystemConfig)
        .filter(SystemConfig.category == ACTIVE_CATEGORY, SystemConfig.config_key == slot_key)
        .first()
    )
    if row is not None:
        db.delete(row)
        db.flush()
    return {
        "platform": normalized_platform,
        "function_type": normalized_function_type,
        "active": False,
        "updated_by": updated_by,
        "updated_at": datetime.utcnow().isoformat(),
    }


def list_algorithm_packages(db: Session) -> dict:
    root = settings.algorithm_package_dir
    active_rows = (
        db.query(SystemConfig)
        .filter(SystemConfig.category == ACTIVE_CATEGORY)
        .all()
    )
    active_mapping = {
        row.config_key: row.config_value
        for row in active_rows
        if isinstance(row.config_value, dict)
    }

    items: list[dict] = []
    if root.exists():
        for platform_dir in sorted([p for p in root.iterdir() if p.is_dir()], key=lambda x: x.name):
            platform = platform_dir.name
            for fn_dir in sorted([p for p in platform_dir.iterdir() if p.is_dir()], key=lambda x: x.name):
                function_type = fn_dir.name
                for version_dir in sorted([p for p in fn_dir.iterdir() if p.is_dir()], key=lambda x: x.name):
                    manifest_path = version_dir / "manifest.json"
                    meta_path = version_dir / "meta.json"
                    if not manifest_path.exists():
                        continue

                    try:
                        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(manifest, dict):
                        continue

                    meta = {}
                    if meta_path.exists():
                        try:
                            parsed = json.loads(meta_path.read_text(encoding="utf-8"))
                            if isinstance(parsed, dict):
                                meta = parsed
                        except json.JSONDecodeError:
                            meta = {}

                    slot_key = make_slot_key(platform, function_type)
                    active = active_mapping.get(slot_key, {})
                    items.append(
                        {
                            "name": manifest.get("name", ""),
                            "platform": platform,
                            "function_type": function_type,
                            "version": version_dir.name,
                            "entry": manifest.get("entry", "main.py"),
                            "uploaded_at": meta.get("uploaded_at"),
                            "uploaded_by": meta.get("uploaded_by"),
                            "smoke_status": meta.get("smoke_status"),
                            "smoke_message": meta.get("smoke_message"),
                            "active": active.get("version") == version_dir.name,
                        }
                    )

    slots = []
    for platform in SUPPORTED_PLATFORMS:
        for function_type in SUPPORTED_FUNCTION_TYPES:
            slot_key = make_slot_key(platform, function_type)
            active = active_mapping.get(slot_key, {})
            slots.append(
                {
                    "platform": platform,
                    "function_type": function_type,
                    "active_name": active.get("name"),
                    "active_version": active.get("version"),
                    "smoke_status": active.get("smoke_status"),
                    "uploaded_at": active.get("uploaded_at"),
                }
            )

    items.sort(key=lambda x: x.get("uploaded_at") or "", reverse=True)
    return {"slots": slots, "items": items}


def get_algorithm_package_archive_path(
    *,
    platform: str,
    function_type: str,
    version: str,
) -> Path:
    normalized_platform, normalized_function_type = _validate_slot(platform, function_type)
    normalized_version = str(version).strip()
    if not _VERSION_PATTERN.fullmatch(normalized_version):
        raise BizError(code=4505, message="version 不合法")

    package_path = _slot_version_dir(normalized_platform, normalized_function_type, normalized_version) / "package.zip"
    if not package_path.exists():
        raise BizError(code=4515, message="算法包不存在", http_status=404)
    return package_path


def get_active_slot_config(db: Session, *, platform: str, function_type: str) -> dict | None:
    normalized_platform, normalized_function_type = _validate_slot(platform, function_type)
    row = (
        db.query(SystemConfig)
        .filter(
            SystemConfig.category == ACTIVE_CATEGORY,
            SystemConfig.config_key == make_slot_key(normalized_platform, normalized_function_type),
        )
        .first()
    )
    if row is None or not isinstance(row.config_value, dict):
        return None
    return row.config_value


def run_active_package(
    db: Session,
    *,
    platform: str,
    function_type: str,
    text: str,
) -> tuple[Any, dict] | None:
    active = get_active_slot_config(db, platform=platform, function_type=function_type)
    if active is None:
        return None

    version = str(active.get("version", "")).strip()
    normalized_platform = platform.strip().lower()
    normalized_function_type = function_type.strip().lower()
    if not version:
        return None
    package_path = _slot_version_dir(normalized_platform, normalized_function_type, version) / "package.zip"
    if not package_path.exists():
        return None

    try:
        entry_path = _normalize_zip_path(
            str(active.get("entry") or _read_manifest_from_dir(normalized_platform, normalized_function_type, version).get("entry") or "main.py")
        )
        result = _run_package_in_subprocess(
            package_path,
            entry_path=entry_path,
            payload=text,
            fallback_payload={"text": text},
        )
        return result, active
    except Exception as exc:
        detail = traceback.format_exc(limit=3)
        raise BizError(code=4532, message=f"算法包执行失败: {exc}\n{detail}") from exc

