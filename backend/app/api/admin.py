from datetime import date, datetime, timedelta
from copy import deepcopy
import ipaddress
import re
import secrets
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants import DEFAULT_BILLING_PACKAGES
from app.deps import (
    current_super_admin,
    db_dep,
    normalize_admin_permissions,
    require_admin_permission,
)
from app.exceptions import BizError
from app.models import (
    AdminAuditLog,
    AdminUser,
    CreditType,
    CreditTransaction,
    LLMErrorLog,
    Order,
    ReferralRelation,
    ReferralReward,
    RegistrationRiskLog,
    SwitchLog,
    SystemConfig,
    SystemSwitch,
    Task,
    TaskType,
    User,
)
from app.pagination import paginate
from app.responses import ok
from app.schemas import (
    APIResp,
    AdminAdjustCreditReq,
    AdminLoginReq,
    AlgoPackageActivateReq,
    AlgoPackageUploadReq,
    ReferralConfigReq,
)
from app.security import create_token, hash_password, verify_password
from app.services.algo_package_service import (
    activate_algorithm_package,
    deactivate_algorithm_package,
    get_active_slot_config,
    get_algorithm_package_archive_path,
    install_algorithm_package,
    list_algorithm_packages,
)
from app.services.builtin_algo_packages import (
    bootstrap_builtin_algo_packages,
    build_authoring_spec_bundle,
    build_builtin_template_package,
)
from app.services.credit_service import change_credits
from app.services.llm_service import LLM_PROVIDER_PRESETS, SUPPORTED_LLM_PROVIDERS, normalize_llm_provider
from app.services.payment_service import DEFAULT_PAYMENT_CONFIG, normalize_payment_provider
from app.services.process_strategy_service import (
    get_process_strategy,
    list_process_strategies,
    normalize_platform,
    normalize_process_mode,
    normalize_task_type,
    update_process_strategy,
)
from app.services.referral_service import get_referral_rules, update_referral_rules

router = APIRouter()
settings = get_settings()

CONFIG_CATEGORIES = {"llm", "payment", "billing", "login", "referral"}
CONFIG_LABELS = {
    "llm": "大模型配置",
    "payment": "支付配置",
    "billing": "计费规则",
    "login": "登录配置",
    "referral": "推广规则",
}
CONFIG_FIELD_LABELS = {
    "llm": {
        "enabled": "启用状态",
        "provider": "提供商",
        "base_url": "Base URL",
        "model": "模型名",
        "api_key": "API Key",
        "timeout_seconds": "超时(秒)",
        "max_output_tokens": "最大输出 Tokens",
        "temperature": "温度",
    },
    "payment": {
        "provider": "支付通道",
        "test_mode": "联调模式",
        "app_id": "应用ID",
        "merchant_id": "商户号",
        "merchant_serial_no": "商户证书序列号",
        "merchant_private_key_pem": "商户私钥",
        "wechatpay_public_key_id": "微信支付公钥ID",
        "wechatpay_public_key": "微信支付公钥",
        "api_v3_key": "APIv3 Key",
        "notify_url": "回调地址",
        "app_private_key_pem": "应用私钥",
        "alipay_public_key": "支付宝公钥",
        "gateway_url": "支付网关",
        "callback_secret": "回调验签密钥",
    },
    "billing": {
        "aigc_rate": "AIGC单价",
        "dedup_rate": "降重单价",
        "rewrite_rate": "降AIGC率单价",
        "packages": "套餐配置",
    },
    "login": {
        "sms_provider": "短信服务商",
        "sms_api_key": "短信网关密钥",
        "sms_gateway_url": "短信网关地址",
        "sms_template_id": "短信模板ID",
        "sms_sign_name": "短信签名",
        "sms_sdk_app_id": "短信应用ID",
        "sms_region": "短信地域",
        "sms_aliyun_region_id": "阿里云地域",
        "sms_access_key_id": "短信AccessKeyId",
        "sms_access_key_secret": "短信AccessKeySecret",
        "debug_code_enabled": "debug验证码",
        "wechat_login_enabled": "微信登录开关",
        "wechat_app_id": "微信AppID",
        "wechat_app_secret": "微信AppSecret",
        "wechat_redirect_uri": "微信回调地址",
        "new_user_initial_credits": "新用户初始积分",
        "max_code_retry": "验证码最大重试次数",
        "phone_lock_minutes": "验证码错误锁定分钟数",
        "send_code_ip_1h_limit": "发送验证码IP限流",
        "login_ip_10m_limit": "登录请求IP限流",
    },
    "referral": {
        "register_inviter_credits": "邀请人注册奖励",
        "register_invitee_bonus": "被邀请人注册福利",
        "first_pay_ratio": "首单返佣比例",
        "recurring_ratio": "复购返佣比例",
        "ip_limit_24h": "同IP注册上限",
    },
}
CONFIG_DEFAULTS = {
    "llm": {
        "enabled": False,
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "api_key": "",
        "timeout_seconds": 25,
        "max_output_tokens": 2048,
        "temperature": 0.3,
    },
    "payment": dict(DEFAULT_PAYMENT_CONFIG),
    "billing": {
        "aigc_rate": 1,
        "dedup_rate": 3,
        "rewrite_rate": 2,
        "packages": deepcopy(DEFAULT_BILLING_PACKAGES),
    },
    "login": {
        "sms_provider": "custom_webhook",
        "sms_api_key": "",
        "sms_gateway_url": "",
        "sms_template_id": "",
        "sms_sign_name": "",
        "sms_sdk_app_id": "",
        "sms_region": "ap-guangzhou",
        "sms_aliyun_region_id": "cn-hangzhou",
        "sms_access_key_id": "",
        "sms_access_key_secret": "",
        "debug_code_enabled": False,
        "wechat_login_enabled": False,
        "wechat_app_id": "",
        "wechat_app_secret": "",
        "wechat_redirect_uri": "",
        "new_user_initial_credits": settings.initial_credits,
        "max_code_retry": settings.max_code_retry,
        "phone_lock_minutes": settings.phone_lock_minutes,
        "send_code_ip_1h_limit": settings.auth_send_code_ip_1h_limit,
        "login_ip_10m_limit": settings.auth_login_ip_10m_limit,
    },
    "referral": {
        "register_inviter_credits": 500,
        "register_invitee_bonus": 500,
        "first_pay_ratio": 0.1,
        "recurring_ratio": 0.05,
        "ip_limit_24h": 3,
    },
}

_LLM_PROVIDERS = set(SUPPORTED_LLM_PROVIDERS)
_PAYMENT_PROVIDERS = {"wechat", "alipay", "mock", "wechatpay_v3"}
_SMS_PROVIDERS = {"custom_webhook", "tencent_sms", "aliyun_sms", "disabled"}
ADMIN_PERMISSION_CATALOG = [
    {"key": "dashboard:view", "label": "查看总览看板", "group": "看板"},
    {"key": "users:view", "label": "查看用户列表与详情", "group": "用户"},
    {"key": "users:manage", "label": "封禁与调整用户积分", "group": "用户"},
    {"key": "tasks:view", "label": "查看任务与结果下载", "group": "任务"},
    {"key": "orders:view", "label": "查看订单列表与详情", "group": "订单"},
    {"key": "orders:refund", "label": "执行订单退款", "group": "订单"},
    {"key": "referrals:view", "label": "查看推广统计与记录", "group": "推广"},
    {"key": "referrals:manage", "label": "修改推广规则与重试奖励", "group": "推广"},
    {"key": "logs:view", "label": "查看系统日志", "group": "日志"},
    {"key": "credits:view", "label": "查看积分流水", "group": "积分"},
    {"key": "algo:view", "label": "查看算法包列表", "group": "算法包"},
    {"key": "algo:manage", "label": "上传/启停算法包", "group": "算法包"},
    {"key": "configs:view", "label": "查看系统配置", "group": "系统配置"},
    {"key": "configs:manage", "label": "修改系统配置", "group": "系统配置"},
    {"key": "system:manage", "label": "切换系统运行模式", "group": "系统模式"},
]
ADMIN_PERMISSION_KEYS = {item["key"] for item in ADMIN_PERMISSION_CATALOG}
DEFAULT_OPERATOR_PERMISSIONS = {
    "dashboard:view",
    "users:view",
    "users:manage",
    "tasks:view",
    "orders:view",
    "orders:refund",
    "referrals:view",
    "logs:view",
    "credits:view",
    "algo:view",
}
ADMIN_USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{2,31}$")


def _effective_admin_permissions(admin: AdminUser) -> list[str]:
    if admin.role == "super_admin":
        return ["*"]
    permissions = normalize_admin_permissions(admin.permissions_json)
    if not permissions:
        permissions = set(DEFAULT_OPERATOR_PERMISSIONS)
    return sorted(permissions)


def _admin_payload(admin: AdminUser) -> dict:
    return {
        "id": admin.id,
        "username": admin.username,
        "role": admin.role,
        "is_active": bool(getattr(admin, "is_active", True)),
        "permissions": _effective_admin_permissions(admin),
        "last_login": admin.last_login,
        "created_at": admin.created_at,
        "updated_at": admin.updated_at,
    }


def _normalize_permission_list(raw) -> list[str]:
    values = normalize_admin_permissions(raw)
    unsupported = sorted(values - ADMIN_PERMISSION_KEYS)
    if unsupported:
        raise BizError(code=4308, message=f"存在不支持的权限: {','.join(unsupported)}")
    return sorted(values)


def _generate_admin_password(length: int = 14) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%&*"
    if length < 12:
        length = 12
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _assert_category(category: str) -> str:
    c = (category or "").strip().lower()
    if c not in CONFIG_CATEGORIES:
        raise BizError(code=4340, message=f"不支持的配置分类:{c}")
    return c


def _as_bool(value, default: bool = False) -> bool:
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


def _as_int(value, *, default: int, min_value: int | None = None, max_value: int | None = None, field: str = "") -> int:
    try:
        num = int(value)
    except Exception as exc:
        raise BizError(code=4341, message=f"{field} 必须是整数") from exc
    if min_value is not None and num < min_value:
        raise BizError(code=4341, message=f"{field} 不能小于 {min_value}")
    if max_value is not None and num > max_value:
        raise BizError(code=4341, message=f"{field} 不能大于 {max_value}")
    return num


def _as_float(
    value,
    *,
    default: float,
    min_value: float | None = None,
    max_value: float | None = None,
    field: str = "",
) -> float:
    try:
        num = float(value)
    except Exception as exc:
        raise BizError(code=4341, message=f"{field} 必须是数字") from exc
    if min_value is not None and num < min_value:
        raise BizError(code=4341, message=f"{field} 不能小于 {min_value}")
    if max_value is not None and num > max_value:
        raise BizError(code=4341, message=f"{field} 不能大于 {max_value}")
    return num


def _as_text(value, *, default: str = "", max_len: int = 256) -> str:
    if value is None:
        return default
    return str(value).strip()[:max_len]


def _is_http_url(value: str) -> bool:
    return bool(value) and value.startswith(("http://", "https://"))


def _is_https_url(value: str) -> bool:
    return bool(value) and value.startswith("https://")


def _has_query_or_fragment(value: str) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return bool(parsed.query or parsed.fragment)


def _default_debug_code_enabled() -> bool:
    return bool(settings.auth_return_debug_code or settings.app_env != "prod")


def _is_private_or_loopback_host(host: str) -> bool:
    normalized = (host or "").strip().lower().strip(".")
    if not normalized:
        return True
    if normalized in {"localhost", "localhost.localdomain"}:
        return True
    if normalized.endswith((".local", ".lan", ".internal", ".home.arpa")):
        return True
    try:
        ip = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _is_public_https_url(value: str) -> bool:
    if not _is_https_url(value):
        return False
    parsed = urlparse(value)
    return bool(parsed.hostname) and (not _is_private_or_loopback_host(parsed.hostname))


def _normalize_billing_packages(value) -> list[dict]:
    packages = value if isinstance(value, list) else []
    normalized: list[dict] = []
    names: set[str] = set()
    if not packages:
        packages = deepcopy(DEFAULT_BILLING_PACKAGES)
    if len(packages) > 12:
        raise BizError(code=4341, message="套餐数量不能超过 12 个")

    for index, item in enumerate(packages, start=1):
        if not isinstance(item, dict):
            raise BizError(code=4341, message=f"套餐第 {index} 项格式错误")
        name = _as_text(item.get("name"), default="", max_len=32)
        if not name:
            raise BizError(code=4341, message=f"套餐第 {index} 项名称不能为空")
        if name in names:
            raise BizError(code=4341, message=f"套餐名称重复: {name}")
        names.add(name)
        price = round(
            _as_float(
                item.get("price", 0),
                default=0,
                min_value=0.01,
                max_value=100000,
                field=f"{name}.price",
            ),
            2,
        )
        credits = _as_int(
            item.get("credits", 0),
            default=0,
            min_value=1,
            max_value=100_000_000,
            field=f"{name}.credits",
        )
        normalized.append(
            {
                "name": name,
                "price": price,
                "credits": credits,
                "description": _as_text(item.get("description"), default="", max_len=120),
                "badge": _as_text(item.get("badge"), default="", max_len=20),
                "enabled": _as_bool(item.get("enabled", True), default=True),
            }
        )
    if not normalized:
        raise BizError(code=4341, message="至少需要配置 1 个套餐")
    if not any(bool(item.get("enabled", False)) for item in normalized):
        raise BizError(code=4341, message="至少需要启用 1 个套餐")
    return normalized


def _normalize_category_payload(category: str, payload: dict) -> dict:
    base = deepcopy(CONFIG_DEFAULTS[category])
    raw = payload if isinstance(payload, dict) else {}

    if category == "billing":
        base["aigc_rate"] = _as_int(raw.get("aigc_rate", base["aigc_rate"]), default=1, min_value=1, max_value=1000, field="aigc_rate")
        base["dedup_rate"] = _as_int(raw.get("dedup_rate", base["dedup_rate"]), default=3, min_value=1, max_value=1000, field="dedup_rate")
        base["rewrite_rate"] = _as_int(
            raw.get("rewrite_rate", base["rewrite_rate"]),
            default=2,
            min_value=1,
            max_value=1000,
            field="rewrite_rate",
        )
        base["packages"] = _normalize_billing_packages(raw.get("packages", base.get("packages", [])))
        return base

    if category == "referral":
        base["register_inviter_credits"] = _as_int(
            raw.get("register_inviter_credits", base["register_inviter_credits"]),
            default=500,
            min_value=0,
            max_value=1_000_000,
            field="register_inviter_credits",
        )
        base["register_invitee_bonus"] = _as_int(
            raw.get("register_invitee_bonus", base["register_invitee_bonus"]),
            default=500,
            min_value=0,
            max_value=1_000_000,
            field="register_invitee_bonus",
        )
        base["first_pay_ratio"] = round(
            _as_float(raw.get("first_pay_ratio", base["first_pay_ratio"]), default=0.1, min_value=0, max_value=1, field="first_pay_ratio"),
            4,
        )
        base["recurring_ratio"] = round(
            _as_float(raw.get("recurring_ratio", base["recurring_ratio"]), default=0.05, min_value=0, max_value=1, field="recurring_ratio"),
            4,
        )
        base["ip_limit_24h"] = _as_int(raw.get("ip_limit_24h", base["ip_limit_24h"]), default=3, min_value=1, max_value=10_000, field="ip_limit_24h")
        return base

    if category == "llm":
        base["enabled"] = _as_bool(raw.get("enabled", base["enabled"]), default=False)
        provider = normalize_llm_provider(_as_text(raw.get("provider", base["provider"]), default="openai", max_len=64))
        preset = LLM_PROVIDER_PRESETS[provider]
        base["provider"] = provider
        base["base_url"] = _as_text(raw.get("base_url") or preset["base_url"], default=preset["base_url"], max_len=256)
        base["model"] = _as_text(raw.get("model") or preset["model"], default=preset["model"], max_len=128)
        base["api_key"] = _as_text(raw.get("api_key", base["api_key"]), default="", max_len=512)
        base["timeout_seconds"] = _as_int(
            raw.get("timeout_seconds", base["timeout_seconds"]),
            default=25,
            min_value=5,
            max_value=180,
            field="timeout_seconds",
        )
        base["max_output_tokens"] = _as_int(
            raw.get("max_output_tokens", base["max_output_tokens"]),
            default=2048,
            min_value=128,
            max_value=8192,
            field="max_output_tokens",
        )
        base["temperature"] = round(
            _as_float(raw.get("temperature", base["temperature"]), default=0.3, min_value=0, max_value=2, field="temperature"),
            2,
        )
        if base["enabled"]:
            if not _is_http_url(base["base_url"]):
                raise BizError(code=4341, message="LLM base_url 必须以 http:// 或 https:// 开头")
            if not base["model"]:
                raise BizError(code=4341, message="启用 LLM 时必须填写 model")
            if not base["api_key"]:
                raise BizError(code=4341, message="启用 LLM 时必须填写 api_key")
        return base

    if category == "payment":
        provider = normalize_payment_provider(_as_text(raw.get("provider", base["provider"]), default="wechatpay_v3", max_len=64))
        if provider and provider not in _PAYMENT_PROVIDERS:
            raise BizError(code=4341, message=f"payment.provider 不支持: {provider}")
        base["provider"] = provider or "wechatpay_v3"
        base["test_mode"] = _as_bool(raw.get("test_mode", base.get("test_mode", settings.payment_test_mode)), default=settings.payment_test_mode)
        base["app_id"] = _as_text(raw.get("app_id", base["app_id"]), default="", max_len=128)
        base["merchant_id"] = _as_text(raw.get("merchant_id", base["merchant_id"]), default="", max_len=128)
        base["merchant_serial_no"] = _as_text(raw.get("merchant_serial_no", base["merchant_serial_no"]), default="", max_len=128)
        base["merchant_private_key_pem"] = _as_text(raw.get("merchant_private_key_pem", base["merchant_private_key_pem"]), default="", max_len=8192)
        base["wechatpay_public_key_id"] = _as_text(raw.get("wechatpay_public_key_id", base["wechatpay_public_key_id"]), default="", max_len=128)
        base["wechatpay_public_key"] = _as_text(raw.get("wechatpay_public_key", base["wechatpay_public_key"]), default="", max_len=8192)
        base["api_v3_key"] = _as_text(raw.get("api_v3_key", base["api_v3_key"]), default="", max_len=64)
        base["notify_url"] = _as_text(raw.get("notify_url", base["notify_url"]), default="", max_len=256)
        base["app_private_key_pem"] = _as_text(raw.get("app_private_key_pem", raw.get("api_key", "")), default="", max_len=8192)
        base["alipay_public_key"] = _as_text(raw.get("alipay_public_key", base.get("alipay_public_key", "")), default="", max_len=8192)
        base["gateway_url"] = _as_text(raw.get("gateway_url", base.get("gateway_url", "")), default="", max_len=256)
        base["api_key"] = _as_text(raw.get("api_key") or raw.get("app_private_key_pem") or base.get("api_key", ""), default="", max_len=8192)
        base["callback_secret"] = _as_text(raw.get("callback_secret", base["callback_secret"]), default="", max_len=512)
        app_private_key = base["app_private_key_pem"] or base["api_key"]
        base["app_private_key_pem"] = app_private_key
        base["api_key"] = app_private_key

        if base["notify_url"] and not _is_http_url(base["notify_url"]):
            raise BizError(code=4341, message="payment.notify_url 必须以 http:// 或 https:// 开头")
        if _has_query_or_fragment(base["notify_url"]):
            raise BizError(code=4341, message="payment.notify_url 不能包含 query 或 fragment")

        if base["gateway_url"] and not _is_http_url(base["gateway_url"]):
            raise BizError(code=4341, message="payment.gateway_url 必须以 http:// 或 https:// 开头")

        if base["provider"] == "mock" and (not base["test_mode"]):
            raise BizError(code=4341, message="payment.provider=mock 仅允许在测试模式下启用")

        if base["provider"] in {"wechat", "wechatpay_v3"}:
            if (not base["test_mode"]) and (not _is_public_https_url(base["notify_url"])):
                raise BizError(code=4341, message="正式微信支付要求 payment.notify_url 为公网 HTTPS 地址")
            required_fields = (
                "app_id",
                "merchant_id",
                "merchant_serial_no",
                "merchant_private_key_pem",
                "api_v3_key",
                "notify_url",
            )
            missing = [field for field in required_fields if not base.get(field)]
            if missing and (not base["test_mode"]):
                raise BizError(code=4341, message=f"微信支付V3缺少必填字段: {','.join(missing)}")
            if base["api_v3_key"] and len(base["api_v3_key"]) != 32:
                raise BizError(code=4341, message="payment.api_v3_key 必须是 32 位字符串")
            if base["merchant_private_key_pem"] and "BEGIN PRIVATE KEY" not in base["merchant_private_key_pem"]:
                raise BizError(code=4341, message="payment.merchant_private_key_pem 格式不正确")
            if bool(base["wechatpay_public_key_id"]) ^ bool(base["wechatpay_public_key"]):
                raise BizError(code=4341, message="wechatpay_public_key_id 和 wechatpay_public_key 必须同时填写")
            if base["wechatpay_public_key"] and "BEGIN PUBLIC KEY" not in base["wechatpay_public_key"]:
                raise BizError(code=4341, message="payment.wechatpay_public_key 格式不正确")

        if base["provider"] in {"custom", "gateway_proxy"} and not base["notify_url"]:
            raise BizError(code=4341, message="网关代理模式必须填写 notify_url")
        if base["provider"] in {"custom", "gateway_proxy"} and (not base["test_mode"]) and (not _is_public_https_url(base["notify_url"])):
            raise BizError(code=4341, message="正式网关代理模式要求 notify_url 为公网 HTTPS 地址")

        if base["provider"] == "alipay" and (not base["test_mode"]) and (
            (not base["app_id"]) or (not base["app_private_key_pem"]) or (not base["alipay_public_key"]) or (not base["notify_url"])
        ):
            raise BizError(code=4341, message="支付宝模式需填写 app_id、app_private_key_pem、alipay_public_key、notify_url")
        if base["provider"] == "alipay" and base["app_private_key_pem"] and ("PRIVATE KEY" not in base.get("app_private_key_pem", "")):
            raise BizError(code=4341, message="payment.app_private_key_pem 格式不正确")
        if base["provider"] == "alipay" and base["alipay_public_key"] and ("PUBLIC KEY" not in base.get("alipay_public_key", "")):
            raise BizError(code=4341, message="payment.alipay_public_key 格式不正确")
        if base["provider"] == "alipay" and (not base["test_mode"]) and (not _is_public_https_url(base["notify_url"])):
            raise BizError(code=4341, message="正式支付宝要求 payment.notify_url 为公网 HTTPS 地址")
        return base

    if category == "login":
        sms_provider = _as_text(raw.get("sms_provider", base["sms_provider"]), default="custom_webhook", max_len=64).lower()
        if sms_provider not in _SMS_PROVIDERS:
            raise BizError(code=4341, message=f"sms_provider 不支持: {sms_provider}")
        base["sms_provider"] = sms_provider
        base["sms_api_key"] = _as_text(raw.get("sms_api_key", base["sms_api_key"]), default="", max_len=512)
        base["sms_gateway_url"] = _as_text(raw.get("sms_gateway_url", base["sms_gateway_url"]), default="", max_len=256)
        base["sms_template_id"] = _as_text(raw.get("sms_template_id", base["sms_template_id"]), default="", max_len=128)
        base["sms_sign_name"] = _as_text(raw.get("sms_sign_name", base["sms_sign_name"]), default="", max_len=128)
        base["sms_sdk_app_id"] = _as_text(raw.get("sms_sdk_app_id", base["sms_sdk_app_id"]), default="", max_len=128)
        base["sms_region"] = _as_text(raw.get("sms_region", base["sms_region"]), default="ap-guangzhou", max_len=64)
        base["sms_aliyun_region_id"] = _as_text(raw.get("sms_aliyun_region_id", base["sms_aliyun_region_id"]), default="cn-hangzhou", max_len=64)
        base["sms_access_key_id"] = _as_text(raw.get("sms_access_key_id", base["sms_access_key_id"]), default="", max_len=256)
        base["sms_access_key_secret"] = _as_text(raw.get("sms_access_key_secret", base["sms_access_key_secret"]), default="", max_len=256)
        base["debug_code_enabled"] = _as_bool(
            raw.get("debug_code_enabled", base["debug_code_enabled"]),
            default=_default_debug_code_enabled(),
        )
        base["wechat_login_enabled"] = _as_bool(raw.get("wechat_login_enabled", base["wechat_login_enabled"]), default=False)
        base["wechat_app_id"] = _as_text(raw.get("wechat_app_id", base["wechat_app_id"]), default="", max_len=128)
        base["wechat_app_secret"] = _as_text(raw.get("wechat_app_secret", base["wechat_app_secret"]), default="", max_len=256)
        base["wechat_redirect_uri"] = _as_text(raw.get("wechat_redirect_uri", base["wechat_redirect_uri"]), default="", max_len=256)
        base["new_user_initial_credits"] = _as_int(
            raw.get("new_user_initial_credits", base["new_user_initial_credits"]),
            default=settings.initial_credits,
            min_value=0,
            max_value=1_000_000,
            field="new_user_initial_credits",
        )
        base["max_code_retry"] = _as_int(
            raw.get("max_code_retry", base["max_code_retry"]),
            default=settings.max_code_retry,
            min_value=1,
            max_value=20,
            field="max_code_retry",
        )
        base["phone_lock_minutes"] = _as_int(
            raw.get("phone_lock_minutes", base["phone_lock_minutes"]),
            default=settings.phone_lock_minutes,
            min_value=1,
            max_value=120,
            field="phone_lock_minutes",
        )
        base["send_code_ip_1h_limit"] = _as_int(
            raw.get("send_code_ip_1h_limit", base["send_code_ip_1h_limit"]),
            default=settings.auth_send_code_ip_1h_limit,
            min_value=1,
            max_value=10_000,
            field="send_code_ip_1h_limit",
        )
        base["login_ip_10m_limit"] = _as_int(
            raw.get("login_ip_10m_limit", base["login_ip_10m_limit"]),
            default=settings.auth_login_ip_10m_limit,
            min_value=1,
            max_value=10_000,
            field="login_ip_10m_limit",
        )

        if base["sms_gateway_url"] and (not _is_http_url(base["sms_gateway_url"])):
            raise BizError(code=4341, message="sms_gateway_url 必须以 http:// 或 https:// 开头")
        if base["wechat_redirect_uri"] and (not _is_https_url(base["wechat_redirect_uri"])):
            raise BizError(code=4341, message="wechat_redirect_uri 必须以 https:// 开头")

        if base["wechat_login_enabled"] and (
            (not base["wechat_app_id"]) or (not base["wechat_app_secret"]) or (not base["wechat_redirect_uri"])
        ):
            raise BizError(code=4341, message="启用微信登录时必须填写 app_id、app_secret、redirect_uri")

        if base["sms_provider"] == "custom_webhook":
            if (not base["debug_code_enabled"]) and (not base["sms_gateway_url"]) and (not base["wechat_login_enabled"]):
                raise BizError(code=4341, message="登录配置至少需可用一种方式：短信网关、微信登录或debug_code")

        if base["sms_provider"] == "tencent_sms":
            required_fields = ("sms_sdk_app_id", "sms_sign_name", "sms_template_id", "sms_access_key_id", "sms_access_key_secret")
            missing = [field for field in required_fields if not base.get(field)]
            if missing and (not base["debug_code_enabled"]) and (not base["wechat_login_enabled"]):
                raise BizError(code=4341, message=f"腾讯云短信缺少字段: {','.join(missing)}")

        if base["sms_provider"] == "aliyun_sms":
            required_fields = ("sms_sign_name", "sms_template_id", "sms_access_key_id", "sms_access_key_secret")
            missing = [field for field in required_fields if not base.get(field)]
            if missing and (not base["debug_code_enabled"]) and (not base["wechat_login_enabled"]):
                raise BizError(code=4341, message=f"阿里云短信缺少字段: {','.join(missing)}")

        if base["sms_provider"] == "disabled" and (not base["debug_code_enabled"]) and (not base["wechat_login_enabled"]):
            raise BizError(code=4341, message="短信关闭后必须启用微信登录或 debug_code")
        return base

    return base


def _category_readiness(category: str, value: dict) -> dict:
    if category == "billing":
        rate_ok = all(int(value.get(k, 0)) > 0 for k in ("aigc_rate", "dedup_rate", "rewrite_rate"))
        packages = value.get("packages") if isinstance(value.get("packages"), list) else []
        enabled_count = sum(1 for item in packages if isinstance(item, dict) and bool(item.get("enabled")))
        pkg_ok = enabled_count >= 1
        ok = rate_ok and pkg_ok
        if not rate_ok:
            message = "计费单价配置异常"
        elif not pkg_ok:
            message = "至少需启用 1 个充值套餐"
        else:
            message = f"计费与套餐已就绪（启用 {enabled_count} 个套餐）"
        return {"category": category, "status": "ready" if ok else "error", "message": message}
    if category == "referral":
        ratio_ok = 0 <= float(value.get("first_pay_ratio", 0)) <= 1 and 0 <= float(value.get("recurring_ratio", 0)) <= 1
        ip_ok = int(value.get("ip_limit_24h", 0)) >= 1
        ok = ratio_ok and ip_ok
        return {"category": category, "status": "ready" if ok else "error", "message": "推广规则已就绪" if ok else "推广规则范围异常"}
    if category == "llm":
        enabled = bool(value.get("enabled"))
        if not enabled:
            return {"category": category, "status": "warning", "message": "LLM 未启用（系统会走算法模式）"}
        fields_ok = bool(value.get("base_url")) and bool(value.get("model")) and bool(value.get("api_key"))
        return {"category": category, "status": "ready" if fields_ok else "error", "message": "LLM 已就绪" if fields_ok else "LLM 关键字段未填全"}
    if category == "payment":
        provider = normalize_payment_provider(str(value.get("provider", "wechatpay_v3")).lower())
        test_mode = bool(value.get("test_mode", settings.payment_test_mode))
        if provider not in _PAYMENT_PROVIDERS:
            return {"category": category, "status": "error", "message": f"支付通道不支持: {provider or 'unknown'}"}
        if test_mode:
            return {"category": category, "status": "warning", "message": "支付处于联调模式（仅开放 mock 支付）"}
        if provider == "mock":
            return {"category": category, "status": "error", "message": "已关闭测试模式，不可使用 mock 支付"}
        if provider in {"wechat", "wechatpay_v3"}:
            required_fields = (
                "app_id",
                "merchant_id",
                "merchant_serial_no",
                "merchant_private_key_pem",
                "api_v3_key",
                "notify_url",
            )
            missing = [field for field in required_fields if not value.get(field)]
            if missing:
                return {"category": category, "status": "error", "message": f"微信支付V3缺少字段: {','.join(missing)}"}
            if len(str(value.get("api_v3_key", ""))) != 32:
                return {"category": category, "status": "error", "message": "api_v3_key 必须是 32 位"}
            if not _is_public_https_url(str(value.get("notify_url", ""))):
                return {"category": category, "status": "error", "message": "微信支付 notify_url 必须是公网 HTTPS 地址"}
            if "BEGIN PRIVATE KEY" not in str(value.get("merchant_private_key_pem", "")):
                return {"category": category, "status": "error", "message": "merchant_private_key_pem 格式不正确"}
            return {"category": category, "status": "ready", "message": "微信支付V3配置已就绪"}
        if provider in {"custom", "gateway_proxy"}:
            if value.get("notify_url") and _is_public_https_url(str(value.get("notify_url", ""))):
                return {"category": category, "status": "warning", "message": "网关代理仅用于外部网关回调，本平台不直连下单"}
            return {"category": category, "status": "error", "message": "网关代理模式缺少 notify_url"}
        if provider == "alipay":
            private_key = str(value.get("app_private_key_pem") or value.get("api_key") or "")
            if (
                value.get("app_id")
                and private_key
                and value.get("alipay_public_key")
                and value.get("notify_url")
                and _is_public_https_url(str(value.get("notify_url", "")))
                and ("PRIVATE KEY" in private_key)
                and ("PUBLIC KEY" in str(value.get("alipay_public_key", "")))
            ):
                return {"category": category, "status": "ready", "message": "支付宝配置已就绪"}
            return {"category": category, "status": "error", "message": "支付宝缺少 app_id / app_private_key_pem / alipay_public_key / notify_url"}
        return {"category": category, "status": "warning", "message": "支付配置待确认"}
    if category == "login":
        debug_enabled = bool(value.get("debug_code_enabled"))
        debug_runtime_enabled = debug_enabled and settings.app_env != "prod"
        sms_provider = str(value.get("sms_provider", "custom_webhook")).lower()
        wechat_enabled = bool(value.get("wechat_login_enabled"))
        sms_ok = False
        wechat_ok = False
        warnings: list[str] = []
        if debug_enabled and settings.app_env == "prod":
            warnings.append("生产环境不会返回 debug_code")

        if sms_provider == "custom_webhook":
            sms_ok = bool(value.get("sms_gateway_url"))
            if not sms_ok:
                warnings.append("未配置短信网关")
        elif sms_provider == "tencent_sms":
            sms_ok = all(
                bool(value.get(field))
                for field in ("sms_sdk_app_id", "sms_sign_name", "sms_template_id", "sms_access_key_id", "sms_access_key_secret")
            )
            if not sms_ok:
                warnings.append("腾讯云短信字段不完整")
        elif sms_provider == "aliyun_sms":
            sms_ok = all(bool(value.get(field)) for field in ("sms_sign_name", "sms_template_id", "sms_access_key_id", "sms_access_key_secret"))
            if not sms_ok:
                warnings.append("阿里云短信字段不完整")
            else:
                warnings.append("请确认阿里云账号已具备目标地区短信发送资质")
        elif sms_provider == "disabled":
            warnings.append("短信登录已关闭")

        if wechat_enabled:
            wechat_ok = all(bool(value.get(field)) for field in ("wechat_app_id", "wechat_app_secret", "wechat_redirect_uri"))
            if not wechat_ok:
                warnings.append("微信登录字段不完整")
            elif not _is_public_https_url(str(value.get("wechat_redirect_uri", ""))):
                warnings.append("微信回调地址需为公网 HTTPS")

        any_login_path = debug_runtime_enabled or sms_ok or wechat_ok
        if not any_login_path:
            return {"category": category, "status": "error", "message": "登录配置不可用：请至少启用一种登录路径"}
        if warnings:
            return {"category": category, "status": "warning", "message": "；".join(warnings)}
        return {"category": category, "status": "ready", "message": "短信与微信登录配置已就绪"}
    return {"category": category, "status": "warning", "message": "未知分类"}


def _get_category_config(db: Session, category: str) -> dict:
    if category == "referral":
        return get_referral_rules(db)
    row = (
        db.query(SystemConfig)
        .filter(SystemConfig.category == "system", SystemConfig.config_key == category)
        .first()
    )
    source = row.config_value if (row and isinstance(row.config_value, dict)) else {}
    merged = deepcopy(CONFIG_DEFAULTS[category])
    if category == "login" and "debug_code_enabled" not in source:
        merged["debug_code_enabled"] = _default_debug_code_enabled()
    merged.update(source)
    if category == "llm":
        provider = normalize_llm_provider(merged.get("provider"))
        preset = LLM_PROVIDER_PRESETS[provider]
        merged["provider"] = provider
        merged["base_url"] = merged.get("base_url") or preset["base_url"]
        merged["model"] = merged.get("model") or preset["model"]
    if category == "payment":
        merged["provider"] = normalize_payment_provider(merged.get("provider"))
        merged["gateway_url"] = _as_text(
            merged.get("gateway_url", DEFAULT_PAYMENT_CONFIG.get("gateway_url", "")),
            default=DEFAULT_PAYMENT_CONFIG.get("gateway_url", ""),
            max_len=256,
        )
        merged["app_private_key_pem"] = _as_text(
            merged.get("app_private_key_pem") or merged.get("api_key"),
            default="",
            max_len=8192,
        )
        merged["api_key"] = _as_text(merged.get("api_key") or merged.get("app_private_key_pem"), default="", max_len=8192)
    if category == "billing":
        try:
            merged["packages"] = _normalize_billing_packages(merged.get("packages"))
        except BizError:
            merged["packages"] = deepcopy(DEFAULT_BILLING_PACKAGES)
    if category == "login":
        merged["sms_provider"] = _as_text(merged.get("sms_provider", "custom_webhook"), default="custom_webhook", max_len=64).lower()
        merged["new_user_initial_credits"] = _as_int(
            merged.get("new_user_initial_credits", settings.initial_credits),
            default=settings.initial_credits,
            min_value=0,
            max_value=1_000_000,
            field="new_user_initial_credits",
        )
        merged["max_code_retry"] = _as_int(
            merged.get("max_code_retry", settings.max_code_retry),
            default=settings.max_code_retry,
            min_value=1,
            max_value=20,
            field="max_code_retry",
        )
        merged["phone_lock_minutes"] = _as_int(
            merged.get("phone_lock_minutes", settings.phone_lock_minutes),
            default=settings.phone_lock_minutes,
            min_value=1,
            max_value=120,
            field="phone_lock_minutes",
        )
        merged["send_code_ip_1h_limit"] = _as_int(
            merged.get("send_code_ip_1h_limit", settings.auth_send_code_ip_1h_limit),
            default=settings.auth_send_code_ip_1h_limit,
            min_value=1,
            max_value=10_000,
            field="send_code_ip_1h_limit",
        )
        merged["login_ip_10m_limit"] = _as_int(
            merged.get("login_ip_10m_limit", settings.auth_login_ip_10m_limit),
            default=settings.auth_login_ip_10m_limit,
            min_value=1,
            max_value=10_000,
            field="login_ip_10m_limit",
        )
    return merged


def _config_label(category: str) -> str:
    return CONFIG_LABELS.get(category, category)


def _config_field_label(category: str, field: str) -> str:
    category_labels = CONFIG_FIELD_LABELS.get(category, {})
    return category_labels.get(field, field)


def _changed_config_fields(before: dict | None, after: dict | None) -> list[str]:
    before_map = before if isinstance(before, dict) else {}
    after_map = after if isinstance(after, dict) else {}
    all_keys = sorted(set(before_map.keys()) | set(after_map.keys()))
    return [key for key in all_keys if before_map.get(key) != after_map.get(key)]


def _config_change_summary(category: str, changed_fields: list[str]) -> str:
    label = _config_label(category)
    if not changed_fields:
        return f"{label} 已重新保存"
    preview = "、".join(_config_field_label(category, field) for field in changed_fields[:3])
    if len(changed_fields) > 3:
        preview = f"{preview} 等 {len(changed_fields)} 项"
    return f"{label} 更新了 {preview}"


def _save_category_config(db: Session, category: str, value: dict, admin: AdminUser) -> dict:
    if category == "referral":
        before = get_referral_rules(db)
        after = update_referral_rules(db, value, admin.id)
        db.add(
            AdminAuditLog(
                admin_id=admin.id,
                action="config_update",
                target_type="referral",
                target_id="rules",
                before_json=before,
                after_json=after,
            )
        )
        db.flush()
        return after

    row = (
        db.query(SystemConfig)
        .filter(SystemConfig.category == "system", SystemConfig.config_key == category)
        .first()
    )
    before = deepcopy(CONFIG_DEFAULTS[category])
    if row is not None and isinstance(row.config_value, dict):
        before = row.config_value
    if row is None:
        row = SystemConfig(
            category="system",
            config_key=category,
            config_value=value,
            updated_by=admin.id,
        )
        db.add(row)
    else:
        row.config_value = value
        row.updated_by = admin.id

    db.add(
        AdminAuditLog(
            admin_id=admin.id,
            action="config_update",
            target_type=category,
            target_id=category,
            before_json=before,
            after_json=value,
        )
    )
    db.flush()
    return value


def _platform_label(platform: str) -> str:
    mapping = {
        "cnki": "知网",
        "vip": "维普",
        "paperpass": "PaperPass",
    }
    return mapping.get(platform, platform)


def _task_type_label(task_type: str) -> str:
    mapping = {
        "aigc_detect": "AIGC检测",
        "rewrite": "降AIGC率",
        "dedup": "降重复率",
    }
    return mapping.get(task_type, task_type)


@router.post("/auth/login", response_model=APIResp)
def admin_login(req: AdminLoginReq, db: Session = Depends(db_dep)) -> APIResp:
    admin = db.query(AdminUser).filter(AdminUser.username == req.username).first()
    if admin is None or not verify_password(req.password, admin.password_hash):
        raise BizError(code=4301, message="管理员账号或密码错误")
    if not bool(getattr(admin, "is_active", True)):
        raise BizError(code=4309, message="管理员账号已停用，请联系超级管理员")
    admin.last_login = datetime.utcnow()
    db.commit()
    token = create_token(subject=str(admin.id), scope="admin")
    return ok(data={"token": token, "admin": _admin_payload(admin), "permission_catalog": ADMIN_PERMISSION_CATALOG})


@router.get("/admin-users", response_model=APIResp)
def list_admin_users(
    keyword: str | None = Query(default=None),
    role: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    _: AdminUser = Depends(current_super_admin),
    db: Session = Depends(db_dep),
) -> APIResp:
    query = db.query(AdminUser)
    if keyword:
        raw = str(keyword).strip()
        if raw:
            query = query.filter(AdminUser.username.like(f"%{raw}%"))
    if role:
        role_val = str(role).strip().lower()
        if role_val in {"super_admin", "operator"}:
            query = query.filter(AdminUser.role == role_val)
    if is_active is not None:
        query = query.filter(AdminUser.is_active == bool(is_active))

    rows = query.order_by(desc(AdminUser.created_at)).all()
    total_count = db.query(func.count(AdminUser.id)).scalar() or 0
    active_count = db.query(func.count(AdminUser.id)).filter(AdminUser.is_active == True).scalar() or 0  # noqa: E712
    inactive_count = max(int(total_count) - int(active_count), 0)
    return ok(
        data={
            "items": [_admin_payload(row) for row in rows],
            "permission_catalog": ADMIN_PERMISSION_CATALOG,
            "summary": {
                "total": int(total_count),
                "active": int(active_count),
                "inactive": int(inactive_count),
            },
        }
    )


@router.post("/admin-users", response_model=APIResp)
def create_admin_user(
    payload: dict,
    admin: AdminUser = Depends(current_super_admin),
    db: Session = Depends(db_dep),
) -> APIResp:
    if not isinstance(payload, dict):
        raise BizError(code=4302, message="请求体必须为 JSON 对象")
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", "")).strip()
    role = str(payload.get("role", "operator")).strip().lower() or "operator"
    is_active = bool(payload.get("is_active", True))
    if len(username) < 3:
        raise BizError(code=4303, message="管理员用户名至少 3 位")
    if not ADMIN_USERNAME_RE.fullmatch(username):
        raise BizError(code=4312, message="用户名仅支持字母开头，且只能包含字母/数字/._-（3~32 位）")
    if len(password) < 8:
        raise BizError(code=4304, message="管理员密码至少 8 位")
    if role == "super_admin":
        raise BizError(code=4305, message="禁止通过该接口创建超级管理员")
    if db.query(AdminUser.id).filter(func.lower(AdminUser.username) == username.lower()).first():
        raise BizError(code=4306, message="管理员用户名已存在")

    permissions = payload.get("permissions")
    if permissions is None:
        normalized_permissions = sorted(DEFAULT_OPERATOR_PERMISSIONS)
    else:
        normalized_permissions = _normalize_permission_list(permissions)
        if not normalized_permissions:
            raise BizError(code=4313, message="至少需要分配 1 项权限")

    row = AdminUser(
        username=username,
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
        permissions_json=normalized_permissions,
    )
    db.add(row)
    db.flush()
    db.add(
        AdminAuditLog(
            admin_id=admin.id,
            action="admin_create",
            target_type="admin_user",
            target_id=str(row.id),
            before_json=None,
            after_json={
                "username": row.username,
                "role": row.role,
                "is_active": row.is_active,
                "permissions": normalized_permissions,
            },
        )
    )
    db.commit()
    db.refresh(row)
    return ok(data={"admin": _admin_payload(row)})


@router.post("/admin-users/{admin_id}/permissions", response_model=APIResp)
def update_admin_permissions(
    admin_id: int,
    payload: dict,
    actor: AdminUser = Depends(current_super_admin),
    db: Session = Depends(db_dep),
) -> APIResp:
    if not isinstance(payload, dict):
        raise BizError(code=4302, message="请求体必须为 JSON 对象")
    target = db.get(AdminUser, admin_id)
    if target is None:
        raise BizError(code=4307, message="管理员不存在", http_status=404)
    if target.role == "super_admin":
        raise BizError(code=4310, message="超级管理员权限固定为全量权限")
    permissions = _normalize_permission_list(payload.get("permissions", []))
    if not permissions:
        raise BizError(code=4313, message="至少需要分配 1 项权限")
    before = _effective_admin_permissions(target)
    target.permissions_json = permissions
    db.add(
        AdminAuditLog(
            admin_id=actor.id,
            action="admin_permissions_update",
            target_type="admin_user",
            target_id=str(target.id),
            before_json={"permissions": before},
            after_json={"permissions": permissions},
        )
    )
    db.commit()
    db.refresh(target)
    return ok(data={"admin": _admin_payload(target)})


@router.post("/admin-users/{admin_id}/password", response_model=APIResp)
def reset_admin_password(
    admin_id: int,
    payload: dict,
    actor: AdminUser = Depends(current_super_admin),
    db: Session = Depends(db_dep),
) -> APIResp:
    if not isinstance(payload, dict):
        raise BizError(code=4302, message="请求体必须为 JSON 对象")
    auto_generate = bool(payload.get("auto_generate", False))
    password = str(payload.get("password", "")).strip()
    if not password and auto_generate:
        password = _generate_admin_password()
    if len(password) < 8:
        raise BizError(code=4304, message="管理员密码至少 8 位")
    target = db.get(AdminUser, admin_id)
    if target is None:
        raise BizError(code=4307, message="管理员不存在", http_status=404)
    target.password_hash = hash_password(password)
    db.add(
        AdminAuditLog(
            admin_id=actor.id,
            action="admin_password_reset",
            target_type="admin_user",
            target_id=str(target.id),
            before_json=None,
            after_json={"password_reset": True},
        )
    )
    db.commit()
    db.refresh(target)
    return ok(
        data={
            "admin": _admin_payload(target),
            "generated_password": password if auto_generate else None,
        }
    )


@router.post("/admin-users/{admin_id}/status", response_model=APIResp)
def update_admin_status(
    admin_id: int,
    payload: dict,
    actor: AdminUser = Depends(current_super_admin),
    db: Session = Depends(db_dep),
) -> APIResp:
    if not isinstance(payload, dict):
        raise BizError(code=4302, message="请求体必须为 JSON 对象")
    target = db.get(AdminUser, admin_id)
    if target is None:
        raise BizError(code=4307, message="管理员不存在", http_status=404)
    next_status = bool(payload.get("is_active", True))
    if actor.id == target.id and not next_status:
        raise BizError(code=4314, message="当前登录管理员账号不可自行停用")
    if target.role == "super_admin" and not next_status:
        raise BizError(code=4311, message="超级管理员账号不可停用")
    before = bool(getattr(target, "is_active", True))
    target.is_active = next_status
    db.add(
        AdminAuditLog(
            admin_id=actor.id,
            action="admin_status_update",
            target_type="admin_user",
            target_id=str(target.id),
            before_json={"is_active": before},
            after_json={"is_active": next_status},
        )
    )
    db.commit()
    db.refresh(target)
    return ok(data={"admin": _admin_payload(target)})


@router.get("/dashboard", response_model=APIResp)
def dashboard(_: AdminUser = Depends(require_admin_permission("dashboard:view")), db: Session = Depends(db_dep)) -> APIResp:
    total_users = db.query(User).count()
    total_tasks = db.query(Task).count()
    total_orders = db.query(Order).filter(Order.status == "paid").count()
    total_revenue = db.query(func.coalesce(func.sum(Order.amount_cny), 0.0)).filter(Order.status == "paid").scalar() or 0

    start_date = date.today() - timedelta(days=29)
    task_rows = (
        db.query(func.date(Task.created_at).label("d"), func.count(Task.id))
        .filter(Task.created_at >= start_date)
        .group_by(func.date(Task.created_at))
        .all()
    )
    revenue_rows = (
        db.query(func.date(Order.created_at).label("d"), func.coalesce(func.sum(Order.amount_cny), 0.0))
        .filter(Order.status == "paid", Order.created_at >= start_date)
        .group_by(func.date(Order.created_at))
        .all()
    )
    task_map = {str(d): int(v) for d, v in task_rows}
    revenue_map = {str(d): float(v) for d, v in revenue_rows}
    trend = []
    for i in range(30):
        d = start_date + timedelta(days=i)
        ds = d.isoformat()
        trend.append({"date": ds, "tasks": task_map.get(ds, 0), "revenue": revenue_map.get(ds, 0.0)})

    by_type = (
        db.query(Task.task_type, func.count(Task.id))
        .group_by(Task.task_type)
        .all()
    )
    type_dist = [{"task_type": t.value if isinstance(t, TaskType) else str(t), "count": int(c)} for t, c in by_type]
    platform_dist = (
        db.query(Task.platform, func.count(Task.id))
        .group_by(Task.platform)
        .all()
    )
    platform_items = [{"platform": p, "count": int(c)} for p, c in platform_dist]
    funnel = {
        "visitors": total_users * 3,
        "registered": total_users,
        "paid_users": db.query(Order.user_id).filter(Order.status == "paid").distinct().count(),
        "task_users": db.query(Task.user_id).distinct().count(),
    }
    switch = db.query(SystemSwitch).first()
    last_switch_log = db.query(SwitchLog).order_by(desc(SwitchLog.created_at)).first()
    return ok(
        data={
            "overview": {
                "total_users": total_users,
                "total_tasks": total_tasks,
                "total_orders": total_orders,
                "total_revenue": round(float(total_revenue), 2),
            },
            "trend_30d": trend,
            "task_type_dist": type_dist,
            "platform_dist": platform_items,
            "funnel": funnel,
            "switch_status": {
                "current_mode": switch.current_mode if switch else "LLM_PLUS_ALGO",
                "llm_fail_count": switch.llm_fail_count if switch else 0,
                "llm_fail_threshold": switch.llm_fail_threshold if switch else 3,
                "last_switch_time": last_switch_log.created_at if last_switch_log else None,
                "last_switch_reason": last_switch_log.reason if last_switch_log else "",
            },
        }
    )


@router.get("/switch/current", response_model=APIResp)
def switch_current(_: AdminUser = Depends(require_admin_permission("dashboard:view")), db: Session = Depends(db_dep)) -> APIResp:
    switch = db.query(SystemSwitch).first()
    if switch is None:
        switch = SystemSwitch(
            current_mode="LLM_PLUS_ALGO",
            llm_enabled=True,
            llm_fail_count=0,
            llm_fail_threshold=3,
        )
        db.add(switch)
        db.commit()
    return ok(
        data={
            "current_mode": switch.current_mode,
            "llm_enabled": switch.llm_enabled,
            "llm_fail_count": switch.llm_fail_count,
            "llm_fail_threshold": switch.llm_fail_threshold,
            "updated_at": switch.updated_at,
        }
    )


@router.post("/switch/mode", response_model=APIResp)
def switch_mode(
    payload: dict,
    admin: AdminUser = Depends(require_admin_permission("system:manage")),
    db: Session = Depends(db_dep),
) -> APIResp:
    mode = str(payload.get("mode", "")).strip().upper()
    if mode not in {"LLM_PLUS_ALGO", "ALGO_ONLY"}:
        raise BizError(code=4342, message="mode 必须为 LLM_PLUS_ALGO 或 ALGO_ONLY")
    switch = db.query(SystemSwitch).first()
    if switch is None:
        switch = SystemSwitch(
            current_mode=mode,
            llm_enabled=True,
            llm_fail_count=0,
            llm_fail_threshold=3,
        )
        db.add(switch)
        db.flush()
    from_mode = switch.current_mode
    switch.current_mode = mode
    if mode == "LLM_PLUS_ALGO":
        switch.llm_fail_count = 0
    db.add(
        SwitchLog(
            from_mode=from_mode,
            to_mode=mode,
            reason=f"manual_switch_by:{admin.username}",
        )
    )
    db.commit()
    return ok(data={"current_mode": switch.current_mode})


@router.get("/switch/logs", response_model=APIResp)
def switch_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: AdminUser = Depends(require_admin_permission("logs:view")),
    db: Session = Depends(db_dep),
) -> APIResp:
    base_query = db.query(SwitchLog)
    total = base_query.count()
    rows = (
        base_query.order_by(desc(SwitchLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        {
            "id": row.id,
            "from_mode": row.from_mode,
            "to_mode": row.to_mode,
            "reason": row.reason,
            "created_at": row.created_at,
        }
        for row in rows
    ]
    return ok(data={"items": items, "pagination": paginate(total, page, page_size)})


@router.get("/llm-error-logs", response_model=APIResp)
def llm_error_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    error_type: str | None = Query(default=None),
    _: AdminUser = Depends(require_admin_permission("logs:view")),
    db: Session = Depends(db_dep),
) -> APIResp:
    base_query = db.query(LLMErrorLog)
    if error_type:
        base_query = base_query.filter(LLMErrorLog.error_type == error_type.strip())
    total = base_query.count()
    rows = (
        base_query.order_by(desc(LLMErrorLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        {
            "id": row.id,
            "task_id": row.task_id,
            "error_type": row.error_type,
            "error_detail": row.error_detail,
            "trigger_downgrade": row.trigger_downgrade,
            "created_at": row.created_at,
        }
        for row in rows
    ]
    return ok(data={"items": items, "pagination": paginate(total, page, page_size)})


@router.get("/users", response_model=APIResp)
def admin_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    q: str | None = Query(default=None),
    _: AdminUser = Depends(require_admin_permission("users:view")),
    db: Session = Depends(db_dep),
) -> APIResp:
    base_query = db.query(User)
    if q:
        base_query = base_query.filter(User.phone.like(f"%{q}%"))
    total = base_query.count()
    rows = (
        base_query.order_by(desc(User.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        {
            "id": u.id,
            "phone": u.phone,
            "nickname": u.nickname,
            "credits": u.credits,
            "is_banned": u.is_banned,
            "created_at": u.created_at,
        }
        for u in rows
    ]
    return ok(data={"items": items, "pagination": paginate(total, page, page_size)})


@router.post("/users/{user_id}/adjust-credits", response_model=APIResp)
def adjust_user_credits(
    user_id: int,
    req: AdminAdjustCreditReq,
    admin: AdminUser = Depends(require_admin_permission("users:manage")),
    db: Session = Depends(db_dep),
) -> APIResp:
    user = db.get(User, user_id)
    if user is None:
        raise BizError(code=4040, message="用户不存在", http_status=404)
    if req.delta == 0:
        raise BizError(code=4302, message="调整值不能为0")
    change_credits(
        db,
        user,
        tx_type=CreditType.ADMIN_ADJUST,
        delta=req.delta,
        reason=f"管理员[{admin.username}]调整积分:{req.reason}",
        related_id=f"admin_adjust:{admin.id}:{datetime.utcnow().timestamp()}",
        source="admin",
    )
    db.commit()
    return ok(data={"user_id": user.id, "credits": user.credits})


@router.post("/users/{user_id}/ban", response_model=APIResp)
def ban_or_unban_user(
    user_id: int,
    payload: dict,
    admin: AdminUser = Depends(require_admin_permission("users:manage")),
    db: Session = Depends(db_dep),
) -> APIResp:
    user = db.get(User, user_id)
    if user is None:
        raise BizError(code=4040, message="用户不存在", http_status=404)
    is_banned = bool(payload.get("is_banned", True))
    user.is_banned = is_banned
    db.add(
        AdminAuditLog(
            admin_id=admin.id,
            action="user_ban_toggle",
            target_type="user",
            target_id=str(user.id),
            before_json={"is_banned": (not is_banned)},
            after_json={"is_banned": is_banned},
        )
    )
    db.commit()
    return ok(data={"user_id": user.id, "is_banned": user.is_banned})


@router.get("/users/{user_id}/detail", response_model=APIResp)
def user_detail(
    user_id: int,
    _: AdminUser = Depends(require_admin_permission("users:view")),
    db: Session = Depends(db_dep),
) -> APIResp:
    user = db.get(User, user_id)
    if user is None:
        raise BizError(code=4040, message="用户不存在", http_status=404)

    tx_rows = (
        db.query(CreditTransaction)
        .filter(CreditTransaction.user_id == user.id)
        .order_by(desc(CreditTransaction.created_at))
        .limit(20)
        .all()
    )
    task_rows = (
        db.query(Task)
        .filter(Task.user_id == user.id)
        .order_by(desc(Task.created_at))
        .limit(20)
        .all()
    )
    orders = db.query(Order).filter(Order.user_id == user.id, Order.status == "paid").all()
    total_paid_cny = round(sum(float(o.amount_cny) for o in orders), 2)
    total_paid_credits = int(sum(int(o.credits) for o in orders))
    total_task_cost = int(
        db.query(func.coalesce(func.sum(Task.cost_credits), 0))
        .filter(Task.user_id == user.id)
        .scalar()
        or 0
    )
    return ok(
        data={
            "user": {
                "id": user.id,
                "phone": user.phone,
                "nickname": user.nickname,
                "credits": user.credits,
                "is_banned": user.is_banned,
                "created_at": user.created_at,
            },
            "summary": {
                "total_paid_cny": total_paid_cny,
                "total_paid_credits": total_paid_credits,
                "total_task_cost_credits": total_task_cost,
            },
            "credit_transactions": [
                {
                    "id": tx.id,
                    "tx_type": tx.tx_type.value,
                    "delta": tx.delta,
                    "balance_before": tx.balance_before,
                    "balance_after": tx.balance_after,
                    "reason": tx.reason,
                    "created_at": tx.created_at,
                }
                for tx in tx_rows
            ],
            "tasks": [
                {
                    "id": t.id,
                    "task_type": t.task_type.value,
                    "platform": t.platform,
                    "status": t.status.value,
                    "char_count": t.char_count,
                    "cost_credits": t.cost_credits,
                    "source_filename": t.source_filename,
                    "report_path": t.report_path,
                    "output_path": t.output_path,
                    "error_message": t.error_message,
                    "result_json": t.result_json,
                    "created_at": t.created_at,
                    "updated_at": t.updated_at,
                }
                for t in task_rows
            ],
        }
    )


@router.get("/tasks", response_model=APIResp)
def admin_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    q_phone: str | None = Query(default=None),
    task_type: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    status: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    _: AdminUser = Depends(require_admin_permission("tasks:view")),
    db: Session = Depends(db_dep),
) -> APIResp:
    base_query = db.query(Task).join(User, User.id == Task.user_id)
    if q_phone:
        base_query = base_query.filter(User.phone.like(f"%{q_phone}%"))
    if task_type:
        try:
            base_query = base_query.filter(Task.task_type == TaskType(task_type))
        except Exception:
            raise BizError(code=4343, message="task_type 不支持")
    if platform:
        base_query = base_query.filter(Task.platform == platform.strip().lower())
    if status:
        try:
            from app.models import TaskStatus

            base_query = base_query.filter(Task.status == TaskStatus(status.strip().lower()))
        except Exception:
            raise BizError(code=4346, message="status 不支持")
    if start_date:
        try:
            dt = datetime.strptime(start_date, "%Y-%m-%d")
            base_query = base_query.filter(Task.created_at >= dt)
        except Exception:
            raise BizError(code=4344, message="start_date 格式应为YYYY-MM-DD")
    if end_date:
        try:
            dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            base_query = base_query.filter(Task.created_at <= dt)
        except Exception:
            raise BizError(code=4345, message="end_date 格式应为YYYY-MM-DD")
    total = base_query.count()
    rows = (
        base_query.order_by(desc(Task.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        {
            "id": t.id,
            "user_id": t.user_id,
            "task_type": t.task_type.value,
            "platform": t.platform,
            "processing_mode": t.processing_mode,
            "status": t.status.value,
            "char_count": t.char_count,
            "cost_credits": t.cost_credits,
            "created_at": t.created_at,
        }
        for t in rows
    ]
    return ok(data={"items": items, "pagination": paginate(total, page, page_size)})


@router.get("/tasks/{task_id}/detail", response_model=APIResp)
def admin_task_detail(
    task_id: int,
    _: AdminUser = Depends(require_admin_permission("tasks:view")),
    db: Session = Depends(db_dep),
) -> APIResp:
    row = db.get(Task, task_id)
    if row is None:
        raise BizError(code=4041, message="任务不存在", http_status=404)
    user = db.get(User, row.user_id)
    return ok(
        data={
            "id": row.id,
            "user_id": row.user_id,
            "user_phone": user.phone if user else "",
            "task_type": row.task_type.value,
            "platform": row.platform,
            "processing_mode": row.processing_mode,
            "status": row.status.value,
            "char_count": row.char_count,
            "cost_credits": row.cost_credits,
            "source_filename": row.source_filename,
            "source_path": row.source_path,
            "report_path": row.report_path,
            "output_path": row.output_path,
            "error_message": row.error_message,
            "result_json": row.result_json,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
    )


@router.get("/tasks/{task_id}/download")
def admin_task_download(
    task_id: int,
    _: AdminUser = Depends(require_admin_permission("tasks:view")),
    db: Session = Depends(db_dep),
) -> FileResponse:
    row = db.get(Task, task_id)
    if row is None:
        raise BizError(code=4041, message="任务不存在", http_status=404)
    if row.status.value != "completed" or not row.output_path:
        raise BizError(code=4108, message="任务尚未完成")
    path = Path(row.output_path)
    if not path.exists():
        raise BizError(code=4109, message="输出文件不存在")
    return FileResponse(path=str(path), filename=path.name)


@router.get("/orders", response_model=APIResp)
def admin_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    q_phone: str | None = Query(default=None),
    order_no: str | None = Query(default=None),
    status: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    _: AdminUser = Depends(require_admin_permission("orders:view")),
    db: Session = Depends(db_dep),
) -> APIResp:
    base_query = db.query(Order).join(User, User.id == Order.user_id)
    if q_phone:
        base_query = base_query.filter(User.phone.like(f"%{q_phone}%"))
    if order_no:
        base_query = base_query.filter(Order.order_no.like(f"%{order_no}%"))
    if status:
        base_query = base_query.filter(Order.status == status.strip().lower())
    if provider:
        base_query = base_query.filter(Order.provider == provider.strip().lower())
    total = base_query.count()
    rows = (
        base_query.order_by(desc(Order.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        {
            "order_no": o.order_no,
            "user_id": o.user_id,
            "amount_cny": o.amount_cny,
            "credits": o.credits,
            "status": o.status,
            "is_first_pay": o.is_first_pay,
            "created_at": o.created_at,
        }
        for o in rows
    ]
    return ok(data={"items": items, "pagination": paginate(total, page, page_size)})


@router.get("/orders/{order_no}/detail", response_model=APIResp)
def order_detail(order_no: str, _: AdminUser = Depends(require_admin_permission("orders:view")), db: Session = Depends(db_dep)) -> APIResp:
    row = db.query(Order).filter(Order.order_no == order_no).first()
    if row is None:
        raise BizError(code=4044, message="订单不存在", http_status=404)
    user = db.get(User, row.user_id)
    return ok(
        data={
            "order_no": row.order_no,
            "user_id": row.user_id,
            "user_phone": user.phone if user else "",
            "amount_cny": row.amount_cny,
            "credits": row.credits,
            "status": row.status,
            "provider": row.provider,
            "is_first_pay": row.is_first_pay,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
    )


@router.post("/orders/{order_no}/refund", response_model=APIResp)
def refund_order(
    order_no: str,
    admin: AdminUser = Depends(require_admin_permission("orders:refund")),
    db: Session = Depends(db_dep),
) -> APIResp:
    order = db.query(Order).filter(Order.order_no == order_no).with_for_update().first()
    if order is None:
        raise BizError(code=4044, message="订单不存在", http_status=404)
    if order.status == "refunded":
        return ok(data={"order_no": order.order_no, "status": order.status, "idempotent": True})
    if order.status != "paid":
        raise BizError(code=4347, message="仅已支付订单可退款")
    user = db.query(User).filter(User.id == order.user_id).with_for_update().first()
    if user is None:
        raise BizError(code=4040, message="用户不存在", http_status=404)
    change_credits(
        db,
        user,
        tx_type=CreditType.ADMIN_ADJUST,
        delta=-int(order.credits),
        reason=f"管理员[{admin.username}]订单退款:{order.order_no}",
        related_id=f"refund:{order.order_no}",
        source="admin",
    )
    order.status = "refunded"
    db.add(
        AdminAuditLog(
            admin_id=admin.id,
            action="order_refund",
            target_type="order",
            target_id=order.order_no,
            before_json={"status": "paid"},
            after_json={"status": "refunded"},
        )
    )
    db.commit()
    return ok(data={"order_no": order.order_no, "status": order.status, "idempotent": False})


@router.get("/referrals/stats", response_model=APIResp)
def referral_stats(_: AdminUser = Depends(require_admin_permission("referrals:view")), db: Session = Depends(db_dep)) -> APIResp:
    total_relations = db.query(ReferralRelation).count()
    total_reward = db.query(func.coalesce(func.sum(ReferralReward.credits), 0)).scalar() or 0
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_relations = db.query(ReferralRelation).filter(ReferralRelation.created_at >= today_start).count()
    top_rows = (
        db.query(ReferralRelation.inviter_id, func.count(ReferralRelation.id).label("cnt"))
        .group_by(ReferralRelation.inviter_id)
        .order_by(desc("cnt"))
        .limit(10)
        .all()
    )
    top10 = [{"inviter_id": uid, "invite_count": int(cnt)} for uid, cnt in top_rows]
    return ok(
        data={
            "total_relations": total_relations,
            "total_reward_credits": int(total_reward),
            "today_new_relations": today_relations,
            "top10": top10,
        }
    )


@router.get("/referrals/rewards", response_model=APIResp)
def referral_rewards(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: AdminUser = Depends(require_admin_permission("referrals:view")),
    db: Session = Depends(db_dep),
) -> APIResp:
    base_query = db.query(ReferralReward)
    total = base_query.count()
    rows = (
        base_query.order_by(desc(ReferralReward.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        {
            "id": r.id,
            "inviter_id": r.inviter_id,
            "invitee_id": r.invitee_id,
            "reward_type": r.reward_type.value,
            "credits": r.credits,
            "status": r.status,
            "retry_count": r.retry_count,
            "ref_order_id": r.ref_order_id,
            "created_at": r.created_at,
        }
        for r in rows
    ]
    return ok(data={"items": items, "pagination": paginate(total, page, page_size)})


@router.get("/referrals/suspicious", response_model=APIResp)
def suspicious_accounts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: AdminUser = Depends(require_admin_permission("referrals:view")),
    db: Session = Depends(db_dep),
) -> APIResp:
    base_query = db.query(RegistrationRiskLog)
    total = base_query.count()
    rows = (
        base_query.order_by(desc(RegistrationRiskLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        {
            "id": row.id,
            "phone": row.phone,
            "ip": row.ip,
            "user_agent": row.user_agent,
            "reason": row.reason,
            "created_at": row.created_at,
        }
        for row in rows
    ]
    return ok(data={"items": items, "pagination": paginate(total, page, page_size)})


@router.post("/referrals/config", response_model=APIResp)
def update_referral_config(
    req: ReferralConfigReq,
    admin: AdminUser = Depends(require_admin_permission("referrals:manage")),
    db: Session = Depends(db_dep),
) -> APIResp:
    data = update_referral_rules(db, req.model_dump(), admin.id)
    db.commit()
    return ok(data=data)


@router.get("/referrals/config", response_model=APIResp)
def get_referral_config(_: AdminUser = Depends(require_admin_permission("referrals:manage")), db: Session = Depends(db_dep)) -> APIResp:
    return ok(data=get_referral_rules(db))


@router.get("/configs/audit-logs", response_model=APIResp)
def config_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: AdminUser = Depends(require_admin_permission("configs:view")),
    db: Session = Depends(db_dep),
) -> APIResp:
    base_query = db.query(AdminAuditLog).filter(AdminAuditLog.action == "config_update")
    total = base_query.count()
    rows = (
        db.query(AdminAuditLog, AdminUser.username)
        .outerjoin(AdminUser, AdminUser.id == AdminAuditLog.admin_id)
        .filter(AdminAuditLog.action == "config_update")
        .order_by(desc(AdminAuditLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = []
    for row, admin_username in rows:
        changed_fields = _changed_config_fields(row.before_json, row.after_json)
        changed_field_labels = [_config_field_label(row.target_type, field) for field in changed_fields]
        items.append(
            {
                "id": row.id,
                "admin_id": row.admin_id,
                "admin_username": admin_username or f"admin#{row.admin_id}",
                "target_type": row.target_type,
                "target_type_label": _config_label(row.target_type),
                "target_id": row.target_id,
                "changed_fields": changed_fields,
                "changed_field_labels": changed_field_labels,
                "changed_count": len(changed_fields),
                "summary": _config_change_summary(row.target_type, changed_fields),
                "created_at": row.created_at,
            }
        )
    return ok(data={"items": items, "pagination": paginate(total, page, page_size)})


@router.get("/configs/readiness", response_model=APIResp)
def get_config_readiness(
    _: AdminUser = Depends(require_admin_permission("configs:view")),
    db: Session = Depends(db_dep),
) -> APIResp:
    items = []
    for c in ("llm", "payment", "billing", "login", "referral"):
        value = _get_category_config(db, c)
        items.append(_category_readiness(c, value))
    return ok(data={"items": items})


@router.get("/configs/{category}", response_model=APIResp)
def get_config(
    category: str,
    _: AdminUser = Depends(require_admin_permission("configs:view")),
    db: Session = Depends(db_dep),
) -> APIResp:
    c = _assert_category(category)
    return ok(data={"category": c, "value": _get_category_config(db, c)})


@router.post("/configs/{category}", response_model=APIResp)
def update_config(
    category: str,
    payload: dict,
    admin: AdminUser = Depends(require_admin_permission("configs:manage")),
    db: Session = Depends(db_dep),
) -> APIResp:
    c = _assert_category(category)
    if not isinstance(payload, dict):
        raise BizError(code=4341, message="配置内容必须为 JSON 对象")
    normalized = _normalize_category_payload(c, payload)
    try:
        value = _save_category_config(db, c, normalized, admin)
        db.commit()
        return ok(data={"category": c, "value": value})
    except Exception:
        db.rollback()
        raise


@router.post("/referrals/rewards/{reward_id}/retry", response_model=APIResp)
def retry_referral_reward(
    reward_id: int,
    _: AdminUser = Depends(require_admin_permission("referrals:manage")),
    db: Session = Depends(db_dep),
) -> APIResp:
    row = db.get(ReferralReward, reward_id)
    if row is None:
        raise BizError(code=4043, message="奖励记录不存在", http_status=404)
    from app.worker_tasks import dispatch_background_task, retry_referral_reward_async

    dispatch_background_task(retry_referral_reward_async, reward_id)
    return ok(data={"reward_id": reward_id, "status": "queued"})


@router.get("/strategies", response_model=APIResp)
def admin_process_strategies(
    _: AdminUser = Depends(require_admin_permission("algo:view")),
    db: Session = Depends(db_dep),
) -> APIResp:
    data = list_process_strategies(db)
    items = []
    for row in data.get("items", []):
        platform = str(row.get("platform", ""))
        task_type = str(row.get("task_type", ""))
        active_slot = get_active_slot_config(db, platform=platform, function_type=task_type)
        item = dict(row)
        item["platform_label"] = _platform_label(platform)
        item["task_type_label"] = _task_type_label(task_type)
        item["active_package"] = (
            {
                "name": active_slot.get("name"),
                "version": active_slot.get("version"),
                "entry": active_slot.get("entry"),
            }
            if isinstance(active_slot, dict)
            else None
        )
        items.append(item)
    return ok(
        data={
            "task_types": data.get("task_types", []),
            "platforms": data.get("platforms", []),
            "items": items,
        }
    )


@router.put("/strategies/{task_type}/{platform}", response_model=APIResp)
def admin_update_process_strategy(
    task_type: str,
    platform: str,
    payload: dict,
    admin: AdminUser = Depends(require_admin_permission("algo:manage")),
    db: Session = Depends(db_dep),
) -> APIResp:
    if not isinstance(payload, dict):
        raise BizError(code=4302, message="请求体必须为 JSON 对象")
    if not any(key in payload for key in ("process_mode", "is_enabled", "timeout_sec")):
        raise BizError(code=4341, message="至少需要提供 process_mode / is_enabled / timeout_sec 其中之一")

    normalized_task_type = normalize_task_type(task_type)
    normalized_platform = normalize_platform(platform)
    before = get_process_strategy(db, task_type=normalized_task_type, platform=normalized_platform)

    process_mode = payload.get("process_mode") if "process_mode" in payload else None
    if process_mode is not None:
        process_mode = normalize_process_mode(process_mode)
    is_enabled = _as_bool(payload.get("is_enabled"), default=False) if "is_enabled" in payload else None
    timeout_sec = payload.get("timeout_sec") if "timeout_sec" in payload else None

    if is_enabled:
        active_slot = get_active_slot_config(
            db,
            platform=normalized_platform,
            function_type=normalized_task_type.value,
        )
        if not active_slot:
            raise BizError(code=4118, message="该平台功能尚未激活算法包，无法启用")

    try:
        result = update_process_strategy(
            db,
            task_type=normalized_task_type,
            platform=normalized_platform,
            process_mode=process_mode,
            is_enabled=is_enabled,
            timeout_sec=timeout_sec,
            updated_by=admin.id,
        )
        db.add(
            AdminAuditLog(
                admin_id=admin.id,
                action="strategy_update",
                target_type="process_strategy",
                target_id=f"{normalized_task_type.value}:{normalized_platform}",
                before_json=before,
                after_json=result,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    active_slot = get_active_slot_config(db, platform=normalized_platform, function_type=normalized_task_type.value)
    result_payload = dict(result)
    result_payload["platform_label"] = _platform_label(normalized_platform)
    result_payload["task_type_label"] = _task_type_label(normalized_task_type.value)
    result_payload["active_package"] = (
        {
            "name": active_slot.get("name"),
            "version": active_slot.get("version"),
            "entry": active_slot.get("entry"),
        }
        if isinstance(active_slot, dict)
        else None
    )
    return ok(data=result_payload)


@router.get("/credit-transactions", response_model=APIResp)
def credit_transactions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: AdminUser = Depends(require_admin_permission("credits:view")),
    db: Session = Depends(db_dep),
) -> APIResp:
    base_query = db.query(CreditTransaction)
    total = base_query.count()
    rows = (
        base_query.order_by(desc(CreditTransaction.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        {
            "id": tx.id,
            "user_id": tx.user_id,
            "tx_type": tx.tx_type.value,
            "delta": tx.delta,
            "balance_before": tx.balance_before,
            "balance_after": tx.balance_after,
            "reason": tx.reason,
            "related_id": tx.related_id,
            "created_at": tx.created_at,
        }
        for tx in rows
    ]
    return ok(data={"items": items, "pagination": paginate(total, page, page_size)})


@router.get("/algo-packages", response_model=APIResp)
def get_algo_packages(_: AdminUser = Depends(require_admin_permission("algo:view")), db: Session = Depends(db_dep)) -> APIResp:
    data = list_algorithm_packages(db)
    return ok(data=data)


@router.get("/algo-packages/guide")
@router.get("/algo-package-guide")
def download_algo_package_guide(_: AdminUser = Depends(require_admin_permission("algo:view"))) -> Response:
    guide_path = Path(__file__).resolve().parents[2] / "docs" / "ALGO_PACKAGE_AUTHORING_GUIDE.md"
    if not guide_path.exists():
        raise BizError(code=4501, message="算法包撰写说明不存在", http_status=404)
    return FileResponse(
        path=guide_path,
        filename=guide_path.name,
        media_type="application/octet-stream",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/algo-packages/authoring-bundle")
def download_algo_package_authoring_bundle(_: AdminUser = Depends(require_admin_permission("algo:view"))) -> Response:
    filename, content = build_authoring_spec_bundle()
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"; filename*=UTF-8\'\'{filename}',
        "Cache-Control": "no-store",
    }
    return Response(content=content, media_type="application/zip", headers=headers)


@router.get("/algo-packages/template")
def download_algo_package_template(
    platform: str = Query(...),
    function_type: str = Query(...),
    _: AdminUser = Depends(require_admin_permission("algo:view")),
) -> Response:
    filename, content = build_builtin_template_package(platform=platform, function_type=function_type)
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"; filename*=UTF-8\'\'{filename}',
        "Cache-Control": "no-store",
    }
    return Response(content=content, media_type="application/zip", headers=headers)


@router.get("/algo-packages/download")
def download_algo_package_archive(
    platform: str = Query(...),
    function_type: str = Query(...),
    version: str = Query(...),
    _: AdminUser = Depends(require_admin_permission("algo:view")),
) -> Response:
    package_path = get_algorithm_package_archive_path(
        platform=platform,
        function_type=function_type,
        version=version,
    )
    filename = f"algo_package_{platform}_{function_type}_{version}.zip"
    return FileResponse(
        path=package_path,
        filename=filename,
        media_type="application/zip",
        headers={"Cache-Control": "no-store"},
    )


@router.post("/algo-packages/bootstrap", response_model=APIResp)
def bootstrap_algo_packages(
    activate: bool = Query(default=True),
    admin: AdminUser = Depends(require_admin_permission("algo:manage")),
    db: Session = Depends(db_dep),
) -> APIResp:
    try:
        data = bootstrap_builtin_algo_packages(
            db,
            uploaded_by=admin.id,
            activate_after_upload=activate,
        )
        db.commit()
        return ok(data=data)
    except Exception:
        db.rollback()
        raise


@router.post("/algo-packages/upload", response_model=APIResp)
def upload_algo_package(
    platform: str = Form(...),
    function_type: str = Form(...),
    activate: bool = Form(default=True),
    admin: AdminUser = Depends(require_admin_permission("algo:manage")),
    db: Session = Depends(db_dep),
    file: UploadFile = File(...),
) -> APIResp:
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise BizError(code=4500, message="仅支持 zip 文件")
    file_bytes = file.file.read()
    req = AlgoPackageUploadReq(platform=platform, function_type=function_type)
    try:
        result = install_algorithm_package(
            db,
            file_bytes=file_bytes,
            platform=req.platform,
            function_type=req.function_type,
            uploaded_by=admin.id,
            activate_after_upload=activate,
        )
        db.commit()
        return ok(data=result)
    except Exception:
        db.rollback()
        raise


@router.post("/algo-packages/activate", response_model=APIResp)
def activate_algo_package(
    req: AlgoPackageActivateReq,
    admin: AdminUser = Depends(require_admin_permission("algo:manage")),
    db: Session = Depends(db_dep),
) -> APIResp:
    try:
        result = activate_algorithm_package(
            db,
            platform=req.platform,
            function_type=req.function_type,
            version=req.version,
            updated_by=admin.id,
        )
        db.commit()
        return ok(data=result)
    except Exception:
        db.rollback()
        raise


@router.post("/algo-packages/deactivate", response_model=APIResp)
def deactivate_algo_package_slot(
    req: AlgoPackageUploadReq,
    admin: AdminUser = Depends(require_admin_permission("algo:manage")),
    db: Session = Depends(db_dep),
) -> APIResp:
    try:
        result = deactivate_algorithm_package(
            db,
            platform=req.platform,
            function_type=req.function_type,
            updated_by=admin.id,
        )
        db.commit()
        return ok(data=result)
    except Exception:
        db.rollback()
        raise
