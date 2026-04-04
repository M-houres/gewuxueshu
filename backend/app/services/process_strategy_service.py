from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.exceptions import BizError
from app.models import SystemConfig, TaskType
from app.services.algo_package_service import get_active_slot_config

STRATEGY_CATEGORY = "process_strategies_v1"

PROCESS_MODE_ALGO_ONLY = "algo_only"
PROCESS_MODE_ALGO_LLM = "algo_llm"
PROCESS_MODES = {PROCESS_MODE_ALGO_ONLY, PROCESS_MODE_ALGO_LLM}

ENGINE_MODE_MAP = {
    PROCESS_MODE_ALGO_ONLY: "ALGO_ONLY",
    PROCESS_MODE_ALGO_LLM: "LLM_PLUS_ALGO",
}

PLATFORM_ALIASES = {
    "cnki": "cnki",
    "zhiwang": "cnki",
    "vip": "vip",
    "weipu": "vip",
    "paperpass": "paperpass",
}

SUPPORTED_PLATFORMS = ("cnki", "vip", "paperpass")
SUPPORTED_TASK_TYPES = tuple(item.value for item in TaskType)


def normalize_platform(raw: str) -> str:
    key = str(raw or "").strip().lower()
    value = PLATFORM_ALIASES.get(key)
    if value:
        return value
    raise BizError(code=4116, message=f"不支持的平台: {raw}")


def normalize_task_type(raw: str | TaskType) -> TaskType:
    if isinstance(raw, TaskType):
        return raw
    try:
        return TaskType(str(raw).strip().lower())
    except Exception as exc:
        raise BizError(code=4101, message="任务类型不支持") from exc


def normalize_process_mode(raw: str | None) -> str:
    value = str(raw or "").strip().lower()
    if value in PROCESS_MODES:
        return value
    if value in {"algo_only", "algo"}:
        return PROCESS_MODE_ALGO_ONLY
    if value in {"algo_llm", "llm_plus_algo", "algo+llm"}:
        return PROCESS_MODE_ALGO_LLM
    raise BizError(code=4342, message="process_mode 必须是 algo_only 或 algo_llm")


def _strategy_key(task_type: TaskType | str, platform: str) -> str:
    t = normalize_task_type(task_type)
    p = normalize_platform(platform)
    return f"{t.value}:{p}"


def _default_strategy(task_type: TaskType, platform: str) -> dict[str, Any]:
    return {
        "task_type": task_type.value,
        "platform": platform,
        "process_mode": PROCESS_MODE_ALGO_ONLY,
        "is_enabled": True,
        "timeout_sec": 300,
        "updated_at": None,
        "updated_by": None,
    }


def _safe_timeout(value: Any, default: int = 300) -> int:
    try:
        timeout = int(value)
    except Exception:
        return default
    if timeout < 30:
        return 30
    if timeout > 3600:
        return 3600
    return timeout


def _safe_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        raw = value.strip().lower()
        if raw in {"1", "true", "yes", "on", "y"}:
            return True
        if raw in {"0", "false", "no", "off", "n", ""}:
            return False
    return default


def _merge_with_row(base: dict[str, Any], row: SystemConfig | None) -> dict[str, Any]:
    data = dict(base)
    if row is None or not isinstance(row.config_value, dict):
        return data
    cfg = row.config_value
    try:
        data["process_mode"] = normalize_process_mode(cfg.get("process_mode"))
    except BizError:
        data["process_mode"] = PROCESS_MODE_ALGO_ONLY
    data["is_enabled"] = _safe_bool(cfg.get("is_enabled"), default=True)
    data["timeout_sec"] = _safe_timeout(cfg.get("timeout_sec"), default=300)
    data["updated_by"] = row.updated_by
    data["updated_at"] = row.updated_at.isoformat() if row.updated_at else None
    return data


def get_process_strategy(
    db: Session,
    *,
    task_type: TaskType | str,
    platform: str,
) -> dict[str, Any]:
    t = normalize_task_type(task_type)
    p = normalize_platform(platform)
    row = (
        db.query(SystemConfig)
        .filter(
            SystemConfig.category == STRATEGY_CATEGORY,
            SystemConfig.config_key == _strategy_key(t, p),
        )
        .first()
    )
    return _merge_with_row(_default_strategy(t, p), row)


def list_process_strategies(db: Session) -> dict[str, Any]:
    rows = db.query(SystemConfig).filter(SystemConfig.category == STRATEGY_CATEGORY).all()
    mapping = {str(row.config_key): row for row in rows}
    items: list[dict[str, Any]] = []
    for task_type in SUPPORTED_TASK_TYPES:
        for platform in SUPPORTED_PLATFORMS:
            key = f"{task_type}:{platform}"
            strategy = _merge_with_row(_default_strategy(TaskType(task_type), platform), mapping.get(key))
            items.append(strategy)
    return {
        "task_types": list(SUPPORTED_TASK_TYPES),
        "platforms": list(SUPPORTED_PLATFORMS),
        "items": items,
    }


def update_process_strategy(
    db: Session,
    *,
    task_type: TaskType | str,
    platform: str,
    process_mode: str | None = None,
    is_enabled: bool | None = None,
    timeout_sec: int | None = None,
    updated_by: int | None = None,
) -> dict[str, Any]:
    t = normalize_task_type(task_type)
    p = normalize_platform(platform)
    key = _strategy_key(t, p)
    row = (
        db.query(SystemConfig)
        .filter(
            SystemConfig.category == STRATEGY_CATEGORY,
            SystemConfig.config_key == key,
        )
        .first()
    )
    current = _merge_with_row(_default_strategy(t, p), row)
    if process_mode is not None:
        current["process_mode"] = normalize_process_mode(process_mode)
    if is_enabled is not None:
        current["is_enabled"] = bool(is_enabled)
    if timeout_sec is not None:
        current["timeout_sec"] = _safe_timeout(timeout_sec, default=current["timeout_sec"])

    payload = {
        "process_mode": current["process_mode"],
        "is_enabled": bool(current["is_enabled"]),
        "timeout_sec": int(current["timeout_sec"]),
    }

    if row is None:
        row = SystemConfig(
            category=STRATEGY_CATEGORY,
            config_key=key,
            config_value=payload,
            updated_by=updated_by,
        )
        db.add(row)
    else:
        row.config_value = payload
        row.updated_by = updated_by
    db.flush()
    return _merge_with_row(current, row)


def resolve_task_processing_mode(
    db: Session,
    *,
    task_type: TaskType | str,
    platform: str,
) -> tuple[str, dict[str, Any]]:
    normalized_task_type = normalize_task_type(task_type)
    normalized_platform = normalize_platform(platform)
    strategy = get_process_strategy(
        db,
        task_type=normalized_task_type,
        platform=normalized_platform,
    )
    if not bool(strategy.get("is_enabled", True)):
        raise BizError(code=4117, message="当前平台暂不支持该功能")

    active_slot = get_active_slot_config(
        db,
        platform=normalized_platform,
        function_type=normalized_task_type.value,
    )
    if not active_slot:
        raise BizError(code=4118, message="当前平台功能尚未配置算法包，请联系管理员")

    mode = str(strategy.get("process_mode", PROCESS_MODE_ALGO_ONLY))
    return ENGINE_MODE_MAP.get(mode, "ALGO_ONLY"), strategy


def sanitize_user_result_json(result_json: Any) -> Any:
    if not isinstance(result_json, dict):
        return result_json
    data = dict(result_json)
    data.pop("mode", None)
    data.pop("processing_mode", None)
    data.pop("llm_used", None)
    data.pop("algo_package_used", None)
    breakdown = data.get("score_breakdown")
    if isinstance(breakdown, dict):
        trimmed = dict(breakdown)
        for key in list(trimmed.keys()):
            lower = str(key).lower()
            if lower.startswith("llm") or "algo_package" in lower or lower in {"blended", "pipeline_mode"}:
                trimmed.pop(key, None)
        data["score_breakdown"] = trimmed
    return data
