from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Mapping
from urllib.parse import quote, urlencode, urlparse

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings
from app.exceptions import BizError
from app.models import Order, SystemConfig

settings = get_settings()

DEFAULT_PAYMENT_CONFIG = {
    "provider": "wechatpay_v3",
    "test_mode": settings.payment_test_mode,
    "app_id": "",
    "merchant_id": "",
    "merchant_serial_no": "",
    "merchant_private_key_pem": "",
    "wechatpay_public_key_id": "",
    "wechatpay_public_key": "",
    "api_v3_key": "",
    "notify_url": "",
    "app_private_key_pem": "",
    "alipay_public_key": "",
    "gateway_url": "https://openapi.alipay.com/gateway.do",
    "callback_secret": "",
}

PAYMENT_PROVIDER_ALIASES = {
    "wechat": "wechatpay_v3",
    "wechatpay_v3": "wechatpay_v3",
    "alipay": "alipay",
    "mock": "mock",
    "gateway_proxy": "gateway_proxy",
    "custom": "gateway_proxy",
}


def normalize_payment_provider(provider: str | None) -> str:
    raw = str(provider or "").strip().lower()
    if raw in PAYMENT_PROVIDER_ALIASES:
        return PAYMENT_PROVIDER_ALIASES[raw]
    return raw or "wechatpay_v3"


def load_payment_config(db) -> dict:
    row = (
        db.query(SystemConfig)
        .filter(SystemConfig.category == "system", SystemConfig.config_key == "payment")
        .first()
    )
    value = row.config_value if row and isinstance(row.config_value, dict) else {}
    merged = dict(DEFAULT_PAYMENT_CONFIG)
    merged.update(value)
    merged["provider"] = normalize_payment_provider(merged.get("provider"))
    merged["test_mode"] = bool(merged.get("test_mode", settings.payment_test_mode))
    merged["gateway_url"] = str(merged.get("gateway_url") or DEFAULT_PAYMENT_CONFIG["gateway_url"]).strip()
    return merged


def enabled_payment_providers(db) -> list[str]:
    cfg = load_payment_config(db)
    if bool(cfg.get("test_mode", settings.payment_test_mode)):
        return ["mock"]
    provider = cfg.get("provider", "wechatpay_v3")
    if provider == "wechatpay_v3":
        return ["wechat"]
    if provider == "alipay":
        return ["alipay"]
    if provider == "mock":
        return ["mock"]
    return []


def build_provider_notify_url(cfg: Mapping[str, Any], provider: str) -> str:
    raw = str(cfg.get("notify_url", "") or "").strip()
    if not raw:
        return ""
    normalized_provider = normalize_payment_provider(provider)
    suffix = "/api/v1/billing/notify/wechatpay" if normalized_provider == "wechatpay_v3" else "/api/v1/billing/notify/alipay"
    parsed = urlparse(raw)
    if parsed.path and parsed.path not in {"", "/"}:
        return raw.rstrip("/")
    return raw.rstrip("/") + suffix


def create_payment_session(db, *, order: Order, package_name: str) -> dict:
    cfg = load_payment_config(db)
    provider = normalize_payment_provider(order.provider)
    if provider == "wechatpay_v3":
        pay_url = _create_wechat_native_order(cfg, order=order, package_name=package_name)
        return {"provider": "wechat", "pay_url": pay_url}
    if provider == "alipay":
        pay_url = _create_alipay_precreate(cfg, order=order, package_name=package_name)
        return {"provider": "alipay", "pay_url": pay_url}
    raise BizError(code=4211, message="当前支付通道不支持直连下单")


def query_remote_order_status(db, *, order: Order) -> dict:
    cfg = load_payment_config(db)
    provider = normalize_payment_provider(order.provider)
    if provider == "wechatpay_v3":
        return _query_wechat_order(cfg, order=order)
    if provider == "alipay":
        return _query_alipay_order(cfg, order=order)
    return {"status": order.status}


def parse_wechatpay_notify(
    db,
    *,
    body: bytes,
    headers: Mapping[str, Any],
) -> dict:
    cfg = load_payment_config(db)
    timestamp = str(headers.get("Wechatpay-Timestamp") or headers.get("wechatpay-timestamp") or "").strip()
    nonce = str(headers.get("Wechatpay-Nonce") or headers.get("wechatpay-nonce") or "").strip()
    signature = str(headers.get("Wechatpay-Signature") or headers.get("wechatpay-signature") or "").strip()
    serial = str(headers.get("Wechatpay-Serial") or headers.get("wechatpay-serial") or "").strip()
    if not all([timestamp, nonce, signature]):
        raise BizError(code=4204, message="微信支付回调签名头缺失")

    try:
        timestamp_int = int(timestamp)
    except Exception as exc:
        raise BizError(code=4205, message="微信支付回调时间戳无效") from exc
    now_ts = int(datetime.now(timezone.utc).timestamp())
    if abs(now_ts - timestamp_int) > settings.payment_callback_ttl_seconds:
        raise BizError(code=4205, message="微信支付回调已过期")

    message = f"{timestamp}\n{nonce}\n{body.decode('utf-8')}\n"
    public_key_pem = _resolve_wechat_public_key(cfg, serial=serial)
    if not _verify_rsa_sha256(public_key_pem, message.encode("utf-8"), signature):
        raise BizError(code=4204, message="微信支付回调验签失败")

    payload = json.loads(body.decode("utf-8"))
    resource = payload.get("resource")
    if not isinstance(resource, dict):
        raise BizError(code=4206, message="微信支付回调缺少 resource")
    resource_json = _decrypt_wechat_resource(cfg, resource)
    trade = json.loads(resource_json)
    trade_state = str(trade.get("trade_state", "")).upper()
    amount = trade.get("amount") or {}
    total_cents = int(amount.get("payer_total") or amount.get("total") or 0)
    return {
        "provider": "wechat",
        "order_no": str(trade.get("out_trade_no", "")).strip(),
        "status": _map_wechat_trade_state(trade_state),
        "amount_cny": round(total_cents / 100, 2) if total_cents else None,
        "provider_trade_no": str(trade.get("transaction_id", "")).strip(),
        "paid_at": str(trade.get("success_time", "")).strip(),
        "raw": trade,
    }


def parse_alipay_notify(form_data: Mapping[str, Any], db) -> dict:
    cfg = load_payment_config(db)
    params: dict[str, str] = {}
    for key, value in form_data.items():
        if isinstance(value, (list, tuple)):
            params[key] = ",".join(str(item) for item in value)
        else:
            params[key] = str(value)
    sign = params.pop("sign", "")
    params.pop("sign_type", None)
    if not sign:
        raise BizError(code=4204, message="支付宝回调缺少 sign")
    if not _verify_alipay_signature(cfg, params, sign):
        raise BizError(code=4204, message="支付宝回调验签失败")
    trade_status = str(params.get("trade_status", "")).upper()
    total_amount = str(params.get("total_amount", "")).strip()
    amount_cny = round(float(total_amount), 2) if total_amount else None
    return {
        "provider": "alipay",
        "order_no": str(params.get("out_trade_no", "")).strip(),
        "status": _map_alipay_trade_status(trade_status),
        "amount_cny": amount_cny,
        "provider_trade_no": str(params.get("trade_no", "")).strip(),
        "paid_at": str(params.get("gmt_payment", "")).strip(),
        "raw": params,
    }


def _canonical_payload(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _resolve_payment_secret(db=None) -> str:
    if db is None:
        return settings.payment_sign_secret
    row = (
        db.query(SystemConfig)
        .filter(SystemConfig.category == "system", SystemConfig.config_key == "payment")
        .first()
    )
    if row and isinstance(row.config_value, dict):
        from_db = str(row.config_value.get("callback_secret", "")).strip()
        if from_db:
            return from_db
    return settings.payment_sign_secret


def sign_payload(payload: Mapping[str, Any], db=None) -> str:
    raw = _canonical_payload(payload).encode("utf-8")
    key = _resolve_payment_secret(db).encode("utf-8")
    return hmac.new(key, raw, hashlib.sha256).hexdigest()


def verify_payload_signature(payload: Mapping[str, Any], signature: str, db=None) -> bool:
    expected = sign_payload(payload, db=db)
    incoming = (signature or "").strip().lower()
    return bool(incoming) and hmac.compare_digest(expected, incoming)


def _create_wechat_native_order(cfg: Mapping[str, Any], *, order: Order, package_name: str) -> str:
    notify_url = build_provider_notify_url(cfg, "wechatpay_v3")
    body_dict = {
        "appid": str(cfg.get("app_id", "")).strip(),
        "mchid": str(cfg.get("merchant_id", "")).strip(),
        "description": f"格物学术 {package_name}",
        "out_trade_no": order.order_no,
        "notify_url": notify_url,
        "amount": {
            "total": int(round(float(order.amount_cny) * 100)),
            "currency": "CNY",
        },
        "time_expire": (datetime.now(timezone.utc) + timedelta(minutes=5)).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    body = json.dumps(body_dict, ensure_ascii=False, separators=(",", ":"))
    path = "/v3/pay/transactions/native"
    headers = _wechat_headers(cfg, method="POST", canonical_url=path, body=body)
    headers["Accept"] = "application/json"
    try:
        response = httpx.post(
            f"https://api.mch.weixin.qq.com{path}",
            content=body.encode("utf-8"),
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.TimeoutException as exc:
        raise BizError(code=4214, message="微信支付下单超时") from exc
    except httpx.HTTPStatusError as exc:
        raise BizError(code=4214, message=f"微信支付下单失败: {exc.response.text[:300]}") from exc
    except httpx.HTTPError as exc:
        raise BizError(code=4214, message=f"微信支付下单失败: {exc}") from exc

    code_url = str(payload.get("code_url", "")).strip()
    if not code_url:
        raise BizError(code=4214, message="微信支付未返回 code_url")
    return code_url


def _query_wechat_order(cfg: Mapping[str, Any], *, order: Order) -> dict:
    path = f"/v3/pay/transactions/out-trade-no/{quote(order.order_no, safe='')}?mchid={quote(str(cfg.get('merchant_id', '')).strip(), safe='')}"
    headers = _wechat_headers(cfg, method="GET", canonical_url=path, body="")
    headers["Accept"] = "application/json"
    try:
        response = httpx.get(
            f"https://api.mch.weixin.qq.com{path}",
            headers=headers,
            timeout=12,
        )
        if response.status_code == 404:
            return {"status": "created"}
        response.raise_for_status()
        payload = response.json()
    except httpx.TimeoutException:
        return {"status": order.status}
    except httpx.HTTPError:
        return {"status": order.status}

    trade_state = str(payload.get("trade_state", "")).upper()
    amount = payload.get("amount") or {}
    total_cents = int(amount.get("payer_total") or amount.get("total") or 0)
    return {
        "status": _map_wechat_trade_state(trade_state),
        "amount_cny": round(total_cents / 100, 2) if total_cents else None,
        "provider_trade_no": str(payload.get("transaction_id", "")).strip(),
        "paid_at": str(payload.get("success_time", "")).strip(),
        "raw": payload,
    }


def _create_alipay_precreate(cfg: Mapping[str, Any], *, order: Order, package_name: str) -> str:
    notify_url = build_provider_notify_url(cfg, "alipay")
    biz_content = {
        "out_trade_no": order.order_no,
        "total_amount": f"{float(order.amount_cny):.2f}",
        "subject": f"格物学术 {package_name}",
        "timeout_express": "5m",
        "product_code": "FACE_TO_FACE_PAYMENT",
    }
    payload = _alipay_request(
        cfg,
        method_name="alipay.trade.precreate",
        biz_content=biz_content,
        notify_url=notify_url,
    )
    qr_code = str(payload.get("qr_code", "")).strip()
    if not qr_code:
        raise BizError(code=4214, message="支付宝下单未返回二维码链接")
    return qr_code


def _query_alipay_order(cfg: Mapping[str, Any], *, order: Order) -> dict:
    try:
        payload = _alipay_request(
            cfg,
            method_name="alipay.trade.query",
            biz_content={"out_trade_no": order.order_no},
        )
    except BizError:
        return {"status": order.status}

    trade_status = str(payload.get("trade_status", "")).upper()
    total_amount = str(payload.get("total_amount", "")).strip()
    amount_cny = round(float(total_amount), 2) if total_amount else None
    return {
        "status": _map_alipay_trade_status(trade_status),
        "amount_cny": amount_cny,
        "provider_trade_no": str(payload.get("trade_no", "")).strip(),
        "paid_at": str(payload.get("send_pay_date", "")).strip(),
        "raw": payload,
    }


def _wechat_headers(cfg: Mapping[str, Any], *, method: str, canonical_url: str, body: str) -> dict[str, str]:
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    serial_no = str(cfg.get("merchant_serial_no", "")).strip()
    mchid = str(cfg.get("merchant_id", "")).strip()
    message = f"{method}\n{canonical_url}\n{timestamp}\n{nonce}\n{body}\n".encode("utf-8")
    signature = _sign_rsa_sha256_base64(str(cfg.get("merchant_private_key_pem", "")).strip(), message)
    authorization = (
        'WECHATPAY2-SHA256-RSA2048 '
        f'mchid="{mchid}",'
        f'nonce_str="{nonce}",'
        f'signature="{signature}",'
        f'timestamp="{timestamp}",'
        f'serial_no="{serial_no}"'
    )
    return {
        "Authorization": authorization,
        "Content-Type": "application/json",
        "User-Agent": "GewuAcademic/1.0",
    }


def _resolve_wechat_public_key(cfg: Mapping[str, Any], *, serial: str) -> str:
    configured_key = str(cfg.get("wechatpay_public_key", "") or "").strip()
    configured_key_id = str(cfg.get("wechatpay_public_key_id", "") or "").strip()
    if configured_key and (not configured_key_id or not serial or configured_key_id == serial):
        return configured_key

    certs = _fetch_wechat_platform_certificates(cfg)
    if serial and serial in certs:
        return certs[serial]
    if configured_key:
        return configured_key
    if certs:
        return next(iter(certs.values()))
    raise BizError(code=4204, message="无法获取微信支付平台公钥")


def _fetch_wechat_platform_certificates(cfg: Mapping[str, Any]) -> dict[str, str]:
    path = "/v3/certificates"
    headers = _wechat_headers(cfg, method="GET", canonical_url=path, body="")
    headers["Accept"] = "application/json"
    try:
        response = httpx.get(
            f"https://api.mch.weixin.qq.com{path}",
            headers=headers,
            timeout=12,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as exc:
        raise BizError(code=4214, message=f"获取微信支付平台证书失败: {exc}") from exc

    certificates: dict[str, str] = {}
    for item in payload.get("data", []):
        encrypt_certificate = item.get("encrypt_certificate") or {}
        serial_no = str(item.get("serial_no", "")).strip()
        if not serial_no:
            continue
        pem = _decrypt_wechat_resource(cfg, encrypt_certificate)
        if pem:
            certificates[serial_no] = pem
    return certificates


def _decrypt_wechat_resource(cfg: Mapping[str, Any], resource: Mapping[str, Any]) -> str:
    key = str(cfg.get("api_v3_key", "") or "").encode("utf-8")
    if len(key) != 32:
        raise BizError(code=4204, message="微信支付 APIv3 Key 无效")
    nonce = str(resource.get("nonce", "") or "").encode("utf-8")
    ciphertext = base64.b64decode(str(resource.get("ciphertext", "") or ""))
    associated_data = str(resource.get("associated_data", "") or "").encode("utf-8")
    try:
        plain = AESGCM(key).decrypt(nonce, ciphertext, associated_data)
    except Exception as exc:
        raise BizError(code=4204, message="微信支付回调解密失败") from exc
    return plain.decode("utf-8")


def _alipay_request(
    cfg: Mapping[str, Any],
    *,
    method_name: str,
    biz_content: Mapping[str, Any],
    notify_url: str | None = None,
) -> dict:
    params = {
        "app_id": str(cfg.get("app_id", "")).strip(),
        "method": method_name,
        "format": "JSON",
        "charset": "utf-8",
        "sign_type": "RSA2",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        "biz_content": json.dumps(biz_content, ensure_ascii=False, separators=(",", ":")),
    }
    if notify_url:
        params["notify_url"] = notify_url
    params["sign"] = _sign_alipay_params(cfg, params)
    gateway_url = str(cfg.get("gateway_url", "") or DEFAULT_PAYMENT_CONFIG["gateway_url"]).strip()
    try:
        response = httpx.post(gateway_url, data=params, timeout=15)
        response.raise_for_status()
        body = response.json()
    except httpx.TimeoutException as exc:
        raise BizError(code=4214, message="支付宝请求超时") from exc
    except httpx.HTTPStatusError as exc:
        raise BizError(code=4214, message=f"支付宝请求失败: {exc.response.text[:300]}") from exc
    except httpx.HTTPError as exc:
        raise BizError(code=4214, message=f"支付宝请求失败: {exc}") from exc

    root_key = method_name.replace(".", "_") + "_response"
    payload = body.get(root_key) if isinstance(body, dict) else None
    if not isinstance(payload, dict):
        raise BizError(code=4214, message="支付宝返回格式异常")
    if str(payload.get("code", "")).strip() != "10000":
        msg = str(payload.get("sub_msg") or payload.get("msg") or "支付宝接口调用失败").strip()
        raise BizError(code=4214, message=msg)
    return payload


def _sign_alipay_params(cfg: Mapping[str, Any], params: Mapping[str, Any]) -> str:
    sign_content = _build_alipay_sign_content(params)
    private_key = str(cfg.get("app_private_key_pem", "") or cfg.get("api_key", "") or "").strip()
    return _sign_rsa_sha256_base64(private_key, sign_content.encode("utf-8"))


def _verify_alipay_signature(cfg: Mapping[str, Any], params: Mapping[str, Any], signature: str) -> bool:
    public_key = str(cfg.get("alipay_public_key", "") or "").strip()
    if not public_key:
        return False
    sign_content = _build_alipay_sign_content(params)
    return _verify_rsa_sha256(public_key, sign_content.encode("utf-8"), signature)


def _build_alipay_sign_content(params: Mapping[str, Any]) -> str:
    parts = []
    for key in sorted(params):
        value = params[key]
        if value is None:
            continue
        text = str(value)
        if text == "":
            continue
        parts.append(f"{key}={text}")
    return "&".join(parts)


def _sign_rsa_sha256_base64(private_key_pem: str, payload: bytes) -> str:
    try:
        private_key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
    except Exception as exc:
        raise BizError(code=4214, message="支付私钥格式无效") from exc
    signature = private_key.sign(payload, padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(signature).decode("ascii")


def _verify_rsa_sha256(public_key_pem: str, payload: bytes, signature: str) -> bool:
    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        public_key.verify(
            base64.b64decode(signature),
            payload,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


def _map_wechat_trade_state(trade_state: str) -> str:
    if trade_state == "SUCCESS":
        return "paid"
    if trade_state in {"CLOSED", "REVOKED", "PAYERROR"}:
        return "closed"
    return "created"


def _map_alipay_trade_status(trade_status: str) -> str:
    if trade_status in {"TRADE_SUCCESS", "TRADE_FINISHED"}:
        return "paid"
    if trade_status == "TRADE_CLOSED":
        return "closed"
    return "created"
