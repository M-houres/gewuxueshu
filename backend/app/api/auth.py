import base64
import hmac
import hashlib
import json
from datetime import datetime
from io import BytesIO
import logging
from urllib.parse import quote
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
import httpx
import qrcode
from sqlalchemy.orm import Session

from app.client_source import DEFAULT_CLIENT_SOURCE, get_client_source
from app.config import get_settings
from app.deps import db_dep, get_redis
from app.exceptions import BizError
from app.models import CreditType, RegistrationRiskLog, SystemConfig, User, UserInviteCode
from app.responses import ok
from app.schemas import APIResp, LoginReq, SendCodeReq
from app.security import create_token
from app.services.credit_service import change_credits
from app.services.referral_service import bind_referral_relation
from app.services.referral_service import get_referral_rules
from app.utils import gen_code, is_phone_valid, make_invite_code

router = APIRouter()
settings = get_settings()
logger = logging.getLogger("app.api.auth")
WX_LOGIN_TTL_SECONDS = 120
DEFAULT_HEADER_NOTICE_TEXT = "平台系统持续优化中，任务提交后请在个人中心查看处理进度。"
_LOGIN_CONFIG_DEFAULTS = {
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
    "header_notice_text": DEFAULT_HEADER_NOTICE_TEXT,
    "new_user_initial_credits": 2000,
    "max_code_retry": 3,
    "phone_lock_minutes": 5,
    "send_code_ip_1h_limit": 30,
    "login_ip_10m_limit": 120,
}


def _default_debug_code_enabled() -> bool:
    return bool(settings.auth_return_debug_code or settings.app_env != "prod")


def _redis_key(phone: str, kind: str) -> str:
    return f"auth:phone:{kind}:{phone}"


def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded:
        return forwarded[:64]
    if request.client is None:
        return ""
    return (request.client.host or "")[:64]


def _get_ua(request: Request) -> str:
    return request.headers.get("user-agent", "")[:280]


def _get_device_fingerprint(request: Request, payload_fp: str | None) -> str:
    # 以 IP+UA 作为主指纹，前端 UUID 仅在极端场景作为兜底
    primary = f"{_get_ip(request)}|{_get_ua(request)}".strip("|")[:128]
    if primary:
        return primary
    direct = (payload_fp or "").strip()[:128]
    if direct:
        return direct
    header_fp = request.headers.get("x-device-fingerprint", "").strip()[:128]
    if header_fp:
        return header_fp
    return "unknown"


def _enforce_ip_limit(
    redis_client,
    *,
    ip: str,
    action: str,
    limit: int,
    window_seconds: int,
    error_code: int,
    error_message: str,
) -> None:
    if not ip or limit <= 0:
        return
    key = f"risk:ip_limit:{action}:{ip}"
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, window_seconds)
    if count > limit:
        raise BizError(code=error_code, message=error_message)


def _user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "phone": user.phone,
        "nickname": user.nickname,
        "credits": user.credits,
        "source": user.source,
        "created_at": user.created_at,
    }


def _get_login_config(db: Session) -> dict:
    row = (
        db.query(SystemConfig)
        .filter(SystemConfig.category == "system", SystemConfig.config_key == "login")
        .first()
    )
    value = row.config_value if row and isinstance(row.config_value, dict) else {}
    merged = dict(_LOGIN_CONFIG_DEFAULTS)
    merged["debug_code_enabled"] = _default_debug_code_enabled()
    merged["new_user_initial_credits"] = int(settings.initial_credits)
    merged["max_code_retry"] = int(settings.max_code_retry)
    merged["phone_lock_minutes"] = int(settings.phone_lock_minutes)
    merged["send_code_ip_1h_limit"] = int(settings.auth_send_code_ip_1h_limit)
    merged["login_ip_10m_limit"] = int(settings.auth_login_ip_10m_limit)
    merged.update(value)
    return merged


def _int_from_login_cfg(
    login_cfg: dict,
    key: str,
    default: int,
    *,
    min_value: int = 0,
    max_value: int | None = None,
) -> int:
    try:
        value = int(login_cfg.get(key, default))
    except Exception:
        value = int(default)
    if value < min_value:
        return int(default)
    if max_value is not None and value > max_value:
        return int(default)
    return value


def _sms_provider_ready(login_cfg: dict) -> bool:
    provider = str(login_cfg.get("sms_provider", "custom_webhook")).strip().lower()
    if provider == "custom_webhook":
        return bool(str(login_cfg.get("sms_gateway_url", settings.sms_gateway_url)).strip())
    if provider == "tencent_sms":
        return all(
            bool(str(login_cfg.get(field, "")).strip())
            for field in ("sms_sdk_app_id", "sms_sign_name", "sms_template_id", "sms_access_key_id", "sms_access_key_secret")
        )
    if provider == "aliyun_sms":
        return all(
            bool(str(login_cfg.get(field, "")).strip())
            for field in ("sms_sign_name", "sms_template_id", "sms_access_key_id", "sms_access_key_secret")
        )
    return False


def _send_via_custom_gateway(phone: str, code: str, login_cfg: dict) -> bool:
    gateway_url = str(login_cfg.get("sms_gateway_url", settings.sms_gateway_url)).strip()
    if not gateway_url:
        return False
    api_key = str(login_cfg.get("sms_api_key", settings.sms_api_key)).strip()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "phone": phone,
        "code": code,
        "provider": str(login_cfg.get("sms_provider", "custom_webhook")).strip() or "custom_webhook",
        "template_id": str(login_cfg.get("sms_template_id", "")).strip(),
        "sign_name": str(login_cfg.get("sms_sign_name", "")).strip(),
        "sdk_app_id": str(login_cfg.get("sms_sdk_app_id", "")).strip(),
    }
    try:
        resp = httpx.post(gateway_url, json=payload, headers=headers, timeout=8)
        return 200 <= resp.status_code < 300
    except Exception:
        return False


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hmac_sha256(key: bytes, text: str) -> bytes:
    return hmac.new(key, text.encode("utf-8"), hashlib.sha256).digest()


def _send_via_tencent_sms(phone: str, code: str, login_cfg: dict) -> bool:
    secret_id = str(login_cfg.get("sms_access_key_id", "")).strip()
    secret_key = str(login_cfg.get("sms_access_key_secret", "")).strip()
    sdk_app_id = str(login_cfg.get("sms_sdk_app_id", "")).strip()
    sign_name = str(login_cfg.get("sms_sign_name", "")).strip()
    template_id = str(login_cfg.get("sms_template_id", "")).strip()
    region = str(login_cfg.get("sms_region", "ap-guangzhou")).strip() or "ap-guangzhou"
    if not all([secret_id, secret_key, sdk_app_id, sign_name, template_id]):
        return False

    normalized_phone = phone if phone.startswith("+") else f"+86{phone}"
    payload = json.dumps(
        {
            "PhoneNumberSet": [normalized_phone],
            "SmsSdkAppId": sdk_app_id,
            "SignName": sign_name,
            "TemplateId": template_id,
            "TemplateParamSet": [code],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )

    host = "sms.tencentcloudapi.com"
    service = "sms"
    action = "SendSms"
    version = "2021-01-11"
    algorithm = "TC3-HMAC-SHA256"
    timestamp = int(datetime.utcnow().timestamp())
    date_str = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
    content_type = "application/json; charset=utf-8"
    signed_headers = "content-type;host;x-tc-action"
    canonical_headers = f"content-type:{content_type}\nhost:{host}\nx-tc-action:{action.lower()}\n"
    canonical_request = "\n".join(["POST", "/", "", canonical_headers, signed_headers, _sha256_hex(payload)])
    credential_scope = f"{date_str}/{service}/tc3_request"
    string_to_sign = "\n".join([algorithm, str(timestamp), credential_scope, _sha256_hex(canonical_request)])
    secret_date = _hmac_sha256(f"TC3{secret_key}".encode("utf-8"), date_str)
    secret_service = hmac.new(secret_date, service.encode("utf-8"), hashlib.sha256).digest()
    secret_signing = hmac.new(secret_service, b"tc3_request", hashlib.sha256).digest()
    signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = (
        f"{algorithm} Credential={secret_id}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    headers = {
        "Authorization": authorization,
        "Content-Type": content_type,
        "Host": host,
        "X-TC-Action": action,
        "X-TC-Timestamp": str(timestamp),
        "X-TC-Version": version,
        "X-TC-Region": region,
    }
    try:
        resp = httpx.post(f"https://{host}", content=payload.encode("utf-8"), headers=headers, timeout=8)
        if not (200 <= resp.status_code < 300):
            return False
        body = resp.json()
        if isinstance(body.get("Response", {}).get("Error"), dict):
            return False
        statuses = body.get("Response", {}).get("SendStatusSet", [])
        if not statuses:
            return False
        return str(statuses[0].get("Code", "")).strip().lower() == "ok"
    except Exception:
        return False


def _aliyun_percent_encode(value: str) -> str:
    return quote(value, safe="~")


def _send_via_aliyun_sms(phone: str, code: str, login_cfg: dict) -> bool:
    access_key_id = str(login_cfg.get("sms_access_key_id", "")).strip()
    access_key_secret = str(login_cfg.get("sms_access_key_secret", "")).strip()
    sign_name = str(login_cfg.get("sms_sign_name", "")).strip()
    template_code = str(login_cfg.get("sms_template_id", "")).strip()
    region_id = str(login_cfg.get("sms_aliyun_region_id", "cn-hangzhou")).strip() or "cn-hangzhou"
    endpoint = str(login_cfg.get("sms_gateway_url", "")).strip() or "https://dysmsapi.aliyuncs.com"
    if not all([access_key_id, access_key_secret, sign_name, template_code]):
        return False

    params = {
        "Action": "SendSms",
        "Version": "2017-05-25",
        "RegionId": region_id,
        "PhoneNumbers": phone,
        "SignName": sign_name,
        "TemplateCode": template_code,
        "TemplateParam": json.dumps({"code": code}, ensure_ascii=False, separators=(",", ":")),
    }
    sorted_pairs = sorted(params.items(), key=lambda item: item[0])
    canonicalized_query = "&".join([f"{_aliyun_percent_encode(str(k))}={_aliyun_percent_encode(str(v))}" for k, v in sorted_pairs])
    query_string = canonicalized_query

    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    nonce = uuid.uuid4().hex
    payload_hash = hashlib.sha256(b"").hexdigest()
    host = endpoint.replace("https://", "").replace("http://", "").strip("/")
    canonical_headers = (
        f"host:{host}\n"
        f"x-acs-action:SendSms\n"
        f"x-acs-content-sha256:{payload_hash}\n"
        f"x-acs-date:{timestamp}\n"
        f"x-acs-signature-nonce:{nonce}\n"
        f"x-acs-version:2017-05-25\n"
    )
    signed_headers = "host;x-acs-action;x-acs-content-sha256;x-acs-date;x-acs-signature-nonce;x-acs-version"
    canonical_request = "\n".join(["POST", "/", query_string, canonical_headers, signed_headers, payload_hash])
    string_to_sign = "ACS3-HMAC-SHA256\n" + hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    signature = hmac.new(access_key_secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = (
        f"ACS3-HMAC-SHA256 Credential={access_key_id},"
        f"SignedHeaders={signed_headers},Signature={signature}"
    )
    headers = {
        "Authorization": authorization,
        "host": host,
        "x-acs-action": "SendSms",
        "x-acs-version": "2017-05-25",
        "x-acs-date": timestamp,
        "x-acs-signature-nonce": nonce,
        "x-acs-content-sha256": payload_hash,
    }
    try:
        resp = httpx.post(f"{endpoint}/?{query_string}", headers=headers, timeout=8)
        if not (200 <= resp.status_code < 300):
            return False
        body = resp.json()
        return str(body.get("Code", "")).strip().upper() == "OK"
    except Exception:
        return False


def _send_sms_code(phone: str, code: str, login_cfg: dict) -> bool:
    provider = str(login_cfg.get("sms_provider", "custom_webhook")).strip().lower()
    if provider == "tencent_sms":
        return _send_via_tencent_sms(phone, code, login_cfg)
    if provider == "aliyun_sms":
        return _send_via_aliyun_sms(phone, code, login_cfg)
    if provider == "disabled":
        return False
    return _send_via_custom_gateway(phone, code, login_cfg)


def _make_virtual_phone(db: Session, openid: str) -> str:
    seed = int(hashlib.sha256(openid.encode("utf-8")).hexdigest()[:16], 16)
    for i in range(2000):
        digits = str((seed + i) % 1_000_000_000).zfill(9)
        phone = f"19{digits}"
        exists = db.query(User.id).filter(User.phone == phone).first()
        if exists is None:
            return phone
    raise BizError(code=4015, message="无法为微信用户分配手机号")


def _wx_key(key: str) -> str:
    return f"auth:wx:{key}"


def _wechat_real_login_enabled(login_cfg: dict) -> bool:
    enabled = bool(login_cfg.get("wechat_login_enabled"))
    if not enabled:
        return False
    return all(
        bool(str(login_cfg.get(field, "")).strip())
        for field in ("wechat_app_id", "wechat_app_secret", "wechat_redirect_uri")
    )


def _wechat_mock_enabled() -> bool:
    return settings.app_env != "prod"


def _wechat_login_enabled(login_cfg: dict) -> bool:
    return _wechat_real_login_enabled(login_cfg) or _wechat_mock_enabled()


def _wechat_authorize_url(login_cfg: dict, state: str) -> str:
    app_id = str(login_cfg.get("wechat_app_id", "")).strip()
    redirect_uri = str(login_cfg.get("wechat_redirect_uri", "")).strip()
    return (
        "https://open.weixin.qq.com/connect/qrconnect"
        f"?appid={quote(app_id, safe='')}"
        f"&redirect_uri={quote(redirect_uri, safe='')}"
        "&response_type=code"
        "&scope=snsapi_login"
        f"&state={quote(state, safe='')}"
        "#wechat_redirect"
    )


def _upsert_wechat_user(
    db: Session,
    *,
    openid: str,
    source: str = DEFAULT_CLIENT_SOURCE,
    scene: str = "web",
    unionid: str | None = None,
    initial_credits: int | None = None,
) -> tuple[User, bool]:
    is_miniprogram = scene == "miniprogram"
    openid_attr = "wechat_openid_mp" if is_miniprogram else "wechat_openid_web"
    openid_column = getattr(User, openid_attr)

    user = db.query(User).filter(openid_column == openid).with_for_update().first()
    if user is None and not is_miniprogram:
        user = db.query(User).filter(User.openid == openid).with_for_update().first()
    if user is None and unionid:
        user = db.query(User).filter(User.wechat_unionid == unionid).with_for_update().first()

    is_new_user = False
    if user and user.is_banned:
        raise BizError(code=4012, message="账号已封禁")
    if user is None:
        is_new_user = True
        phone = _make_virtual_phone(db, openid)
        user = User(
            phone=phone,
            nickname=f"微信用户{phone[-4:]}",
            openid=openid if not is_miniprogram else None,
            wechat_unionid=unionid,
            wechat_openid_web=openid if not is_miniprogram else None,
            wechat_openid_mp=openid if is_miniprogram else None,
            source=source,
            credits=0,
        )
        db.add(user)
        db.flush()
        change_credits(
            db,
            user,
            tx_type=CreditType.INIT,
            delta=settings.initial_credits if initial_credits is None else int(initial_credits),
            reason="微信新用户初始积分",
            related_id=f"wx_user_init:{user.id}",
            source=source,
        )
        db.add(UserInviteCode(user_id=user.id, invite_code=make_invite_code(user.id)))
        db.flush()
        return user, is_new_user

    setattr(user, openid_attr, openid)
    if not is_miniprogram and not user.openid:
        user.openid = openid
    if unionid and not user.wechat_unionid:
        user.wechat_unionid = unionid
    if not user.source:
        user.source = source
    db.flush()
    return user, is_new_user


@router.get("/options", response_model=APIResp)
def auth_options(db: Session = Depends(db_dep)) -> APIResp:
    login_cfg = _get_login_config(db)
    debug_enabled = bool(login_cfg.get("debug_code_enabled"))
    phone_login_enabled = _sms_provider_ready(login_cfg) or (settings.app_env != "prod" and debug_enabled)
    header_notice_text = str(login_cfg.get("header_notice_text", DEFAULT_HEADER_NOTICE_TEXT) or "").strip()
    if not header_notice_text:
        header_notice_text = DEFAULT_HEADER_NOTICE_TEXT
    return ok(
        data={
            "wechat_login_enabled": _wechat_login_enabled(login_cfg),
            "wechat_auth_scenes": ["web", "miniprogram"],
            "debug_code_enabled": debug_enabled,
            "sms_provider": str(login_cfg.get("sms_provider", "custom_webhook")).strip().lower() or "custom_webhook",
            "wx_mock_enabled": _wechat_mock_enabled(),
            "phone_login_enabled": phone_login_enabled,
            "new_user_initial_credits": _int_from_login_cfg(login_cfg, "new_user_initial_credits", settings.initial_credits, min_value=0, max_value=1_000_000),
            "header_notice_text": header_notice_text,
        }
    )


@router.post("/send-code", response_model=APIResp)
def send_code(
    req: SendCodeReq,
    request: Request,
    db: Session = Depends(db_dep),
    redis_client=Depends(get_redis),
) -> APIResp:
    login_cfg = _get_login_config(db)
    if not is_phone_valid(req.phone):
        raise BizError(code=4001, message="手机号格式错误")
    ip = _get_ip(request)
    _enforce_ip_limit(
        redis_client,
        ip=ip,
        action="send_code",
        limit=_int_from_login_cfg(login_cfg, "send_code_ip_1h_limit", settings.auth_send_code_ip_1h_limit, min_value=1, max_value=10_000),
        window_seconds=3600,
        error_code=4019,
        error_message="当前IP请求验证码过于频繁，请稍后重试",
    )

    lock_key = _redis_key(req.phone, "lock")
    cooldown_key = _redis_key(req.phone, "cooldown")
    code_key = _redis_key(req.phone, "code")
    attempt_key = _redis_key(req.phone, "attempt")

    if redis_client.ttl(lock_key) > 0:
        raise BizError(code=4004, message=f"手机号已锁定，请稍后再试({redis_client.ttl(lock_key)}s)")
    if redis_client.ttl(cooldown_key) > 0:
        raise BizError(code=4003, message=f"验证码发送过于频繁，请{redis_client.ttl(cooldown_key)}秒后重试")

    debug_switch = bool(login_cfg.get("debug_code_enabled"))
    sms_ready = _sms_provider_ready(login_cfg)
    if settings.app_env == "prod" and (not sms_ready):
        logger.warning("auth_send_code_sms_not_configured", extra={"ip": ip, "phone_tail": req.phone[-4:]})
        raise BizError(code=4021, message="短信服务未配置或未就绪，当前环境不可发送验证码")

    code = gen_code()
    sms_sent = _send_sms_code(req.phone, code, login_cfg)
    allow_debug_fallback = settings.app_env != "prod" and debug_switch
    if (not sms_sent) and (not allow_debug_fallback):
        logger.warning(
            "auth_send_code_gateway_failed",
            extra={"ip": ip, "phone_tail": req.phone[-4:]},
        )
        raise BizError(code=4022, message="短信发送失败，请检查短信配置")

    redis_client.setex(code_key, 300, code)
    redis_client.setex(attempt_key, 300, 0)
    redis_client.setex(cooldown_key, 60, 1)
    payload = {"phone": req.phone, "expire_seconds": 300}
    if settings.app_env != "prod" and debug_switch:
        payload["debug_code"] = code
    logger.info(
        "auth_send_code_success",
        extra={"ip": ip, "phone_tail": req.phone[-4:], "sms_sent": sms_sent},
    )
    return ok(data=payload)


@router.post("/login", response_model=APIResp)
def login(req: LoginReq, request: Request, db: Session = Depends(db_dep), redis_client=Depends(get_redis)) -> APIResp:
    login_cfg = _get_login_config(db)
    if not is_phone_valid(req.phone):
        raise BizError(code=4001, message="手机号格式错误")
    _enforce_ip_limit(
        redis_client,
        ip=_get_ip(request),
        action="login",
        limit=_int_from_login_cfg(login_cfg, "login_ip_10m_limit", settings.auth_login_ip_10m_limit, min_value=1, max_value=10_000),
        window_seconds=10 * 60,
        error_code=4020,
        error_message="当前IP登录请求过于频繁，请稍后再试",
    )

    lock_key = _redis_key(req.phone, "lock")
    cooldown_key = _redis_key(req.phone, "cooldown")
    code_key = _redis_key(req.phone, "code")
    attempt_key = _redis_key(req.phone, "attempt")

    lock_ttl = redis_client.ttl(lock_key)
    if lock_ttl > 0:
        raise BizError(code=4004, message=f"验证码错误次数过多，请{lock_ttl}秒后再试")

    real_code = redis_client.get(code_key)
    if not real_code:
        raise BizError(code=4002, message="验证码已过期，请重新发送")

    if req.code != real_code:
        current_retry = redis_client.incr(attempt_key)
        redis_client.expire(attempt_key, 300)
        max_code_retry = _int_from_login_cfg(login_cfg, "max_code_retry", settings.max_code_retry, min_value=1, max_value=20)
        phone_lock_minutes = _int_from_login_cfg(login_cfg, "phone_lock_minutes", settings.phone_lock_minutes, min_value=1, max_value=120)
        if current_retry >= max_code_retry:
            redis_client.setex(lock_key, phone_lock_minutes * 60, 1)
            redis_client.delete(code_key)
        raise BizError(code=4005, message="验证码错误")

    redis_client.delete(code_key, attempt_key, cooldown_key)

    ip = _get_ip(request)
    ua = _get_ua(request)
    fp = _get_device_fingerprint(request, req.device_fingerprint)
    client_source = get_client_source(request)
    is_new_user = False
    register_relation_id: int | None = None

    try:
        user = db.query(User).filter(User.phone == req.phone).with_for_update().first()
        if user and user.is_banned:
            db.add(
                RegistrationRiskLog(
                    phone=req.phone,
                    ip=ip,
                    user_agent=ua,
                    reason="banned_user_login_attempt",
                )
            )
            db.commit()
            raise BizError(code=4012, message="账号已封禁")

        if user is None:
            is_new_user = True
            user = User(phone=req.phone, nickname=f"用户{req.phone[-4:]}", source=client_source, credits=0)
            db.add(user)
            db.flush()
            initial_credits = _int_from_login_cfg(
                login_cfg,
                "new_user_initial_credits",
                settings.initial_credits,
                min_value=0,
                max_value=1_000_000,
            )
            change_credits(
                db,
                user,
                tx_type=CreditType.INIT,
                delta=initial_credits,
                reason="新用户初始积分",
                related_id=f"user_init:{user.id}",
                source=client_source,
            )
            db.add(UserInviteCode(user_id=user.id, invite_code=make_invite_code(user.id)))
            db.flush()

            relation = None
            if req.referrer_code:
                relation = bind_referral_relation(
                    db,
                    invitee=user,
                    referrer_code=req.referrer_code.strip().upper(),
                    source=client_source,
                )

            suspicious = False
            if relation:
                inviter_fp = redis_client.get(f"user:fp:{relation.inviter_id}")
                ip_key = f"risk:register_ip:{ip}"
                rules = get_referral_rules(db)
                ip_limit = int(rules.get("ip_limit_24h", 3))
                ip_count = redis_client.incr(ip_key) if ip else 0
                if ip and ip_count == 1:
                    redis_client.expire(ip_key, 24 * 3600)
                if ip and ip_count > ip_limit:
                    suspicious = True
                    db.add(
                        RegistrationRiskLog(
                            phone=req.phone,
                            ip=ip,
                            user_agent=ua,
                            reason=f"same_ip_over_{ip_limit}_24h",
                        )
                    )

                fp_hash = hashlib.sha256(fp.encode("utf-8")).hexdigest()
                fp_key = f"risk:register_fp:{fp_hash}"
                fp_count = redis_client.incr(fp_key)
                if fp_count == 1:
                    redis_client.expire(fp_key, 24 * 3600)
                if fp_count > 3:
                    suspicious = True
                    db.add(
                        RegistrationRiskLog(
                            phone=req.phone,
                            ip=ip,
                            user_agent=ua,
                            reason="same_device_over_3_24h",
                        )
                    )
                if inviter_fp and inviter_fp == fp:
                    suspicious = True
                    db.add(
                        RegistrationRiskLog(
                            phone=req.phone,
                            ip=ip,
                            user_agent=ua,
                            reason="same_device_with_inviter",
                        )
                    )
                if not suspicious:
                    register_relation_id = relation.id
        elif not user.source:
            user.source = client_source

        token = create_token(subject=str(user.id), scope="user")
        redis_client.setex(f"user:fp:{user.id}", 30 * 24 * 3600, fp)
        db.commit()
    except Exception:
        db.rollback()
        raise

    if register_relation_id:
        from app.worker_tasks import dispatch_background_task, grant_register_rewards_async

        dispatch_background_task(grant_register_rewards_async, register_relation_id)

    logger.info(
        "auth_login_success",
        extra={"user_id": user.id, "is_new_user": is_new_user, "ip": ip},
    )
    return ok(
        data={
            "token": token,
            "is_new_user": is_new_user,
            "user": _user_payload(user),
        }
    )


@router.get("/wx/qrcode", response_model=APIResp)
def wx_qrcode(db: Session = Depends(db_dep), redis_client=Depends(get_redis)) -> APIResp:
    login_cfg = _get_login_config(db)
    if not _wechat_login_enabled(login_cfg):
        raise BizError(code=4016, message="微信登录未启用或配置不完整")

    raw = f"{datetime.utcnow().timestamp()}-{gen_code()}-{settings.jwt_secret}"
    key = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    state = f"{key}.{gen_code()}"
    data = {"status": "pending", "created_at": int(datetime.utcnow().timestamp()), "state": state}
    redis_client.setex(_wx_key(key), WX_LOGIN_TTL_SECONDS, json.dumps(data, ensure_ascii=False))

    if _wechat_real_login_enabled(login_cfg):
        qr_payload = _wechat_authorize_url(login_cfg, state)
    else:
        qr_payload = f"mock://wechat-login?state={quote(state, safe='')}"
    img = qrcode.make(qr_payload)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return ok(
        data={
            "key": key,
            "qrcode_data_url": f"data:image/png;base64,{encoded}",
            "expire_seconds": WX_LOGIN_TTL_SECONDS,
            "poll_interval_seconds": 2,
        }
    )


@router.get("/wx/callback", response_class=HTMLResponse)
def wx_callback(
    request: Request,
    code: str = "",
    state: str = "",
    db: Session = Depends(db_dep),
    redis_client=Depends(get_redis),
):
    if not code or not state:
        raise BizError(code=4017, message="微信授权参数缺失")
    if "." not in state:
        raise BizError(code=4017, message="无效的微信授权状态")
    key = state.split(".", 1)[0]
    raw = redis_client.get(_wx_key(key))
    if not raw:
        raise BizError(code=4018, message="二维码已过期，请刷新")
    try:
        pending = json.loads(raw)
    except Exception as exc:
        raise BizError(code=4018, message="微信登录会话已失效，请刷新二维码") from exc
    if str(pending.get("state", "")) != state:
        raise BizError(code=4017, message="微信授权状态校验失败")

    login_cfg = _get_login_config(db)
    if not _wechat_real_login_enabled(login_cfg):
        raise BizError(code=4016, message="微信真实登录未启用或配置不完整")

    app_id = str(login_cfg.get("wechat_app_id", "")).strip()
    app_secret = str(login_cfg.get("wechat_app_secret", "")).strip()
    token_resp = httpx.get(
        "https://api.weixin.qq.com/sns/oauth2/access_token",
        params={
            "appid": app_id,
            "secret": app_secret,
            "code": code,
            "grant_type": "authorization_code",
        },
        timeout=8,
    )
    if not (200 <= token_resp.status_code < 300):
        raise BizError(code=4016, message="微信授权换取令牌失败")
    token_data = token_resp.json()
    openid = str(token_data.get("openid", "")).strip()
    unionid = str(token_data.get("unionid", "")).strip() or None
    if not openid:
        err_msg = token_data.get("errmsg") or "微信返回openid为空"
        raise BizError(code=4016, message=f"微信授权失败: {err_msg}")

    try:
        user, is_new_user = _upsert_wechat_user(
            db,
            openid=openid,
            source=get_client_source(request),
            scene="web",
            unionid=unionid,
            initial_credits=_int_from_login_cfg(
                login_cfg,
                "new_user_initial_credits",
                settings.initial_credits,
                min_value=0,
                max_value=1_000_000,
            ),
        )
        token = create_token(subject=str(user.id), scope="user")
        db.commit()
    except Exception:
        db.rollback()
        raise

    wx_payload = {
        "status": "authorized",
        "token": token,
        "user": _user_payload(user),
        "is_new_user": is_new_user,
    }
    redis_client.setex(_wx_key(key), WX_LOGIN_TTL_SECONDS, json.dumps(wx_payload, ensure_ascii=False, default=str))
    return HTMLResponse(
        content=(
            "<html><head><meta charset='utf-8'></head><body>"
            "<div style='font-family: sans-serif;padding:24px;'>"
            "<h3>微信授权成功</h3><p>可返回原页面，系统将自动完成登录。</p>"
            "</div></body></html>"
        )
    )


@router.get("/wx/poll/{key}", response_model=APIResp)
def wx_poll(key: str, redis_client=Depends(get_redis)) -> APIResp:
    raw = redis_client.get(_wx_key(key))
    if not raw:
        return ok(data={"status": "expired"})
    try:
        data = json.loads(raw)
    except Exception:
        redis_client.delete(_wx_key(key))
        return ok(data={"status": "expired"})
    status = str(data.get("status", "pending"))
    if status != "authorized":
        return ok(data={"status": "pending"})
    token = data.get("token")
    user_data = data.get("user")
    if not token or not isinstance(user_data, dict):
        return ok(data={"status": "pending"})
    redis_client.delete(_wx_key(key))
    return ok(data={"status": "authorized", "token": token, "user": user_data})


@router.post("/wx/mock-authorize", response_model=APIResp)
def wx_mock_authorize(
    payload: dict,
    request: Request,
    db: Session = Depends(db_dep),
    redis_client=Depends(get_redis),
) -> APIResp:
    if settings.app_env == "prod":
        raise BizError(code=4016, message="生产环境禁止 mock 微信授权")
    key = str(payload.get("key", "")).strip()
    if not key:
        raise BizError(code=4017, message="缺少微信登录 key")
    raw = redis_client.get(_wx_key(key))
    if not raw:
        raise BizError(code=4018, message="二维码已过期，请刷新")

    openid = str(payload.get("openid", "")).strip()
    if not openid:
        openid = f"mock_wx_{hashlib.sha256((key + settings.jwt_secret).encode('utf-8')).hexdigest()[:16]}"
    scene = str(payload.get("scene", "web")).strip().lower() or "web"
    if scene not in {"web", "miniprogram"}:
        scene = "web"
    unionid = str(payload.get("unionid", "")).strip() or None
    login_cfg = _get_login_config(db)

    try:
        user, is_new_user = _upsert_wechat_user(
            db,
            openid=openid,
            source=get_client_source(request),
            scene=scene,
            unionid=unionid,
            initial_credits=_int_from_login_cfg(
                login_cfg,
                "new_user_initial_credits",
                settings.initial_credits,
                min_value=0,
                max_value=1_000_000,
            ),
        )
        token = create_token(subject=str(user.id), scope="user")
        db.commit()
    except Exception:
        db.rollback()
        raise

    wx_payload = {
        "status": "authorized",
        "token": token,
        "user": _user_payload(user),
        "is_new_user": is_new_user,
    }
    redis_client.setex(_wx_key(key), WX_LOGIN_TTL_SECONDS, json.dumps(wx_payload, ensure_ascii=False, default=str))
    return ok(data={"status": "authorized"})
