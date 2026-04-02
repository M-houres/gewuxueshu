import base64
from datetime import datetime, timezone
from io import BytesIO
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, PlainTextResponse
import qrcode
from sqlalchemy.orm import Session

from app.client_source import DEFAULT_CLIENT_SOURCE, SYSTEM_CLIENT_SOURCE, get_client_source
from app.config import get_settings
from app.constants import DEFAULT_BILLING_PACKAGES, PACKAGE_CONFIG
from app.deps import current_user, db_dep
from app.exceptions import BizError
from app.models import CreditTransaction, CreditType, Order, SystemConfig, User
from app.responses import ok
from app.schemas import APIResp, CreateOrderReq, MockPayReq, PayCallbackReq
from app.services.credit_service import change_credits
from app.services.payment_service import (
    create_payment_session,
    enabled_payment_providers,
    load_payment_config,
    normalize_payment_provider,
    parse_alipay_notify,
    parse_wechatpay_notify,
    query_remote_order_status,
    verify_payload_signature,
)
from app.utils import make_order_no

router = APIRouter()
settings = get_settings()
logger = logging.getLogger("app.api.billing")
ORDER_PAY_TIMEOUT_SECONDS = 300
SUPPORTED_PROVIDERS = {"wechat", "alipay", "mock"}
PACKAGE_NAME_ALIASES = {
    "年费包": "大额包",
}


def _normalize_package_name(name: str) -> str:
    raw = str(name or "").strip()
    return PACKAGE_NAME_ALIASES.get(raw, raw)


def _load_available_packages(db: Session) -> list[dict]:
    row = (
        db.query(SystemConfig)
        .filter(SystemConfig.category == "system", SystemConfig.config_key == "billing")
        .first()
    )
    cfg = row.config_value if row and isinstance(row.config_value, dict) else {}
    raw_packages = cfg.get("packages")
    normalized: list[dict] = []
    seen_names: set[str] = set()

    if isinstance(raw_packages, list):
        for item in raw_packages:
            if not isinstance(item, dict):
                continue
            name = _normalize_package_name(item.get("name", ""))
            if not name or name in seen_names:
                continue
            try:
                price = round(float(item.get("price", 0)), 2)
                credits = int(item.get("credits", 0))
            except Exception:
                continue
            enabled = bool(item.get("enabled", True))
            if price <= 0 or credits <= 0 or (not enabled):
                continue
            seen_names.add(name)
            normalized.append(
                {
                    "name": name,
                    "price": price,
                    "credits": credits,
                    "description": str(item.get("description", "")).strip(),
                    "badge": str(item.get("badge", "")).strip(),
                }
            )

    if normalized:
        return normalized

    return [
        {
            "name": _normalize_package_name(item["name"]),
            "price": round(float(item["price"]), 2),
            "credits": int(item["credits"]),
            "description": str(item.get("description", "")).strip(),
            "badge": str(item.get("badge", "")).strip(),
        }
        for item in DEFAULT_BILLING_PACKAGES
        if bool(item.get("enabled", True))
    ]


def _find_package(db: Session, package_name: str) -> dict | None:
    normalized_name = _normalize_package_name(package_name)
    by_name = {item["name"]: item for item in _load_available_packages(db)}
    package = by_name.get(normalized_name)
    if package:
        return package
    # backward compatibility fallback for historical constant-only orders
    legacy = PACKAGE_CONFIG.get(normalized_name) or PACKAGE_CONFIG.get(package_name)
    if legacy:
        return {
            "name": normalized_name,
            "price": round(float(legacy["price"]), 2),
            "credits": int(legacy["credits"]),
            "description": "",
            "badge": "",
        }
    return None


def _settle_package_order(
    db: Session,
    *,
    user: User,
    package_name: str,
    order_no: str,
    provider: str,
    amount_cny: float | None = None,
    source: str | None = None,
) -> tuple[Order, bool]:
    pkg = _find_package(db, package_name)
    if pkg is None:
        raise BizError(code=4201, message="套餐不存在")
    expected_amount = round(float(pkg["price"]), 2)
    paid_amount = expected_amount if amount_cny is None else round(float(amount_cny), 2)
    if paid_amount != expected_amount:
        raise BizError(code=4207, message="支付金额与套餐价格不匹配")

    locked_user = db.query(User).filter(User.id == user.id).with_for_update().first()
    if locked_user is None:
        raise BizError(code=4040, message="用户不存在", http_status=404)

    order = db.query(Order).filter(Order.order_no == order_no).with_for_update().first()
    if order and order.user_id != user.id:
        raise BizError(code=4208, message="订单归属用户不匹配")
    if order and order.status == "paid":
        return order, True

    credits = int(pkg["credits"])
    order_source = source or getattr(user, "source", "") or DEFAULT_CLIENT_SOURCE
    if order is None:
        has_paid = (
            db.query(Order)
            .filter(Order.user_id == user.id, Order.status == "paid")
            .count()
            > 0
        )
        order = Order(
            order_no=order_no,
            user_id=user.id,
            amount_cny=paid_amount,
            credits=credits,
            source=order_source,
            status="paid",
            provider=provider,
            is_first_pay=not has_paid,
        )
        db.add(order)
        db.flush()
    else:
        paid_count = (
            db.query(Order)
            .filter(
                Order.user_id == user.id,
                Order.status == "paid",
                Order.id != order.id,
            )
            .count()
        )
        order.amount_cny = paid_amount
        order.credits = credits
        if not order.source:
            order.source = order_source
        order.status = "paid"
        order.provider = provider
        order.is_first_pay = paid_count == 0
        db.flush()

    existed_tx = (
        db.query(CreditTransaction)
        .filter(
            CreditTransaction.user_id == user.id,
            CreditTransaction.tx_type == CreditType.PACKAGE_PAY,
            CreditTransaction.related_id == order_no,
        )
        .first()
    )
    if existed_tx:
        return order, True

    change_credits(
        db,
        locked_user,
        tx_type=CreditType.PACKAGE_PAY,
        delta=credits,
        reason=f"购买套餐:{package_name}",
        related_id=order_no,
        source=order.source or order_source,
    )
    return order, False


def _build_qrcode_data(pay_url: str) -> str:
    img = qrcode.make(pay_url)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _pay_pending_order(db: Session, order: Order) -> tuple[Order, bool]:
    if order.status == "paid":
        return order, True
    if order.status == "refunded":
        raise BizError(code=4209, message="订单已退款，不可重复支付")
    if order.status == "closed":
        raise BizError(code=4210, message="订单已关闭，请重新下单")

    existing_tx = (
        db.query(CreditTransaction)
        .filter(
            CreditTransaction.user_id == order.user_id,
            CreditTransaction.tx_type == CreditType.PACKAGE_PAY,
            CreditTransaction.related_id == order.order_no,
        )
        .first()
    )
    if existing_tx:
        order.status = "paid"
        db.flush()
        return order, True

    user = db.query(User).filter(User.id == order.user_id).with_for_update().first()
    if user is None:
        raise BizError(code=4040, message="用户不存在", http_status=404)
    has_paid = (
        db.query(Order)
        .filter(Order.user_id == order.user_id, Order.status == "paid", Order.id != order.id)
        .count()
        > 0
    )
    order.status = "paid"
    order.is_first_pay = not has_paid
    change_credits(
        db,
        user,
        tx_type=CreditType.PACKAGE_PAY,
        delta=order.credits,
        reason=f"支付订单:{order.order_no}",
        related_id=order.order_no,
        source=order.source or getattr(user, "source", "") or DEFAULT_CLIENT_SOURCE,
    )
    db.flush()
    return order, False


def _calc_remain_seconds(order: Order) -> int:
    delta = datetime.utcnow() - order.created_at
    elapsed = int(delta.total_seconds())
    return max(0, ORDER_PAY_TIMEOUT_SECONDS - elapsed)


def _default_mock_pay_url(order_no: str) -> str:
    return f"{settings.frontend_base_url.rstrip('/')}/app/buy?order_no={order_no}&provider=mock"


def _trigger_referral_reward(order: Order, *, idempotent: bool) -> None:
    if idempotent:
        return
    from app.worker_tasks import dispatch_background_task, grant_order_referral_rewards_async

    dispatch_background_task(grant_order_referral_rewards_async, order.id)


def _assert_paid_amount_matches(order: Order, amount_cny: float | None) -> None:
    if amount_cny is None:
        return
    actual = round(float(amount_cny), 2)
    expected = round(float(order.amount_cny), 2)
    if abs(actual - expected) > 0.01:
        raise BizError(code=4207, message="支付金额与订单金额不匹配")


def _settle_existing_order(
    db: Session,
    *,
    order_no: str,
    provider: str,
    amount_cny: float | None = None,
) -> tuple[Order, bool]:
    order = db.query(Order).filter(Order.order_no == order_no).with_for_update().first()
    if order is None:
        raise BizError(code=4044, message="订单不存在", http_status=404)
    _assert_paid_amount_matches(order, amount_cny)
    order.provider = provider
    settled_order, idempotent = _pay_pending_order(db, order)
    return settled_order, idempotent


def _wechat_ack(success: bool, message: str) -> JSONResponse:
    if success:
        return JSONResponse(status_code=200, content={"code": "SUCCESS", "message": message})
    return JSONResponse(status_code=400, content={"code": "FAIL", "message": message})


@router.get("/packages", response_model=APIResp)
def packages(db: Session = Depends(db_dep)) -> APIResp:
    payment_cfg = load_payment_config(db)
    payment_test_mode = bool(payment_cfg.get("test_mode", settings.payment_test_mode))
    supported_providers = enabled_payment_providers(db)
    payment_mode = payment_cfg.get("provider", "wechatpay_v3")
    items = _load_available_packages(db)
    return ok(
        data={
            "items": items,
            "payment_test_mode": payment_test_mode,
            "message": "当前为联调支付模式" if payment_test_mode else "当前为正式支付模式",
            "supported_providers": supported_providers,
            "payment_provider_mode": payment_mode,
        }
    )


@router.post("/create-order", response_model=APIResp)
def create_order(
    req: CreateOrderReq,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(db_dep),
) -> APIResp:
    pkg = _find_package(db, req.package_name)
    if pkg is None:
        raise BizError(code=4201, message="套餐不存在")
    provider = req.provider.strip().lower()
    enabled = set(enabled_payment_providers(db))
    payment_cfg = load_payment_config(db)
    payment_test_mode = bool(payment_cfg.get("test_mode", settings.payment_test_mode))
    if provider not in SUPPORTED_PROVIDERS or provider not in enabled:
        raise BizError(code=4211, message="支付方式不支持")
    if provider == "mock" and not payment_test_mode:
        raise BizError(code=4213, message="当前环境未开启测试支付")

    order_no = make_order_no()
    client_source = get_client_source(request)
    order = Order(
        order_no=order_no,
        user_id=user.id,
        amount_cny=float(pkg["price"]),
        credits=int(pkg["credits"]),
        source=client_source,
        status="created",
        provider=provider,
        is_first_pay=False,
    )
    db.add(order)
    db.flush()

    pay_url = _default_mock_pay_url(order_no)
    if provider != "mock":
        session = create_payment_session(db, order=order, package_name=req.package_name)
        pay_url = str(session.get("pay_url", "")).strip()
        if not pay_url:
            raise BizError(code=4214, message="支付通道未返回支付链接")

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    logger.info(
        "billing_order_created",
        extra={
            "order_no": order_no,
            "user_id": user.id,
            "provider": provider,
            "amount_cny": order.amount_cny,
        },
    )
    return ok(
        data={
            "order_no": order_no,
            "status": order.status,
            "provider": provider,
            "amount_cny": order.amount_cny,
            "credits": order.credits,
            "expire_seconds": ORDER_PAY_TIMEOUT_SECONDS,
            "qrcode_data_url": _build_qrcode_data(pay_url),
            "payment_test_mode": payment_test_mode,
        }
    )


@router.get("/order-status/{order_no}", response_model=APIResp)
def order_status(order_no: str, user: User = Depends(current_user), db: Session = Depends(db_dep)) -> APIResp:
    order = db.query(Order).filter(Order.order_no == order_no, Order.user_id == user.id).with_for_update().first()
    if order is None:
        raise BizError(code=4044, message="订单不存在", http_status=404)
    if order.status == "created":
        remain = _calc_remain_seconds(order)
        if remain <= 0:
            order.status = "closed"
            db.commit()
            return ok(
                data={
                    "order_no": order.order_no,
                    "status": "closed",
                    "remain_seconds": 0,
                    "provider": order.provider,
                }
            )

        if normalize_payment_provider(order.provider) in {"wechatpay_v3", "alipay"}:
            remote = query_remote_order_status(db, order=order)
            remote_status = str(remote.get("status", "created")).lower()
            if remote_status == "paid":
                try:
                    settled_order, idempotent = _settle_existing_order(
                        db,
                        order_no=order.order_no,
                        provider=order.provider,
                        amount_cny=remote.get("amount_cny"),
                    )
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
                _trigger_referral_reward(settled_order, idempotent=idempotent)
                return ok(
                    data={
                        "order_no": settled_order.order_no,
                        "status": settled_order.status,
                        "remain_seconds": 0,
                        "provider": settled_order.provider,
                    }
                )
            if remote_status == "closed":
                order.status = "closed"
                db.commit()
                return ok(
                    data={
                        "order_no": order.order_no,
                        "status": "closed",
                        "remain_seconds": 0,
                        "provider": order.provider,
                    }
                )

        return ok(
            data={
                "order_no": order.order_no,
                "status": order.status,
                "remain_seconds": remain,
                "provider": order.provider,
            }
        )
    return ok(
        data={
            "order_no": order.order_no,
            "status": order.status,
            "remain_seconds": 0,
            "provider": order.provider,
        }
    )


@router.post("/order-pay/{order_no}", response_model=APIResp)
def order_pay(order_no: str, user: User = Depends(current_user), db: Session = Depends(db_dep)) -> APIResp:
    order = db.query(Order).filter(Order.order_no == order_no, Order.user_id == user.id).with_for_update().first()
    if order is None:
        raise BizError(code=4044, message="订单不存在", http_status=404)
    payment_cfg = load_payment_config(db)
    payment_test_mode = bool(payment_cfg.get("test_mode", settings.payment_test_mode))
    if order.status == "created" and _calc_remain_seconds(order) <= 0:
        order.status = "closed"
        db.commit()
        raise BizError(code=4212, message="订单已超时，请重新下单")

    if normalize_payment_provider(order.provider) != "mock" and not payment_test_mode:
        remote = query_remote_order_status(db, order=order)
        if str(remote.get("status", "")).lower() != "paid":
            raise BizError(code=4215, message="请在微信或支付宝完成支付后再刷新订单状态")
        try:
            settled_order, idempotent = _settle_existing_order(
                db,
                order_no=order.order_no,
                provider=order.provider,
                amount_cny=remote.get("amount_cny"),
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        _trigger_referral_reward(settled_order, idempotent=idempotent)
        return ok(
            data={
                "order_no": settled_order.order_no,
                "status": settled_order.status,
                "idempotent": idempotent,
                "credits": settled_order.credits,
            }
        )

    try:
        settled_order, idempotent = _pay_pending_order(db, order)
        db.commit()
    except Exception:
        db.rollback()
        raise

    _trigger_referral_reward(settled_order, idempotent=idempotent)
    logger.info(
        "billing_order_paid",
        extra={
            "order_no": settled_order.order_no,
            "user_id": user.id,
            "provider": settled_order.provider,
            "idempotent": idempotent,
        },
    )
    return ok(data={"order_no": settled_order.order_no, "status": settled_order.status, "idempotent": idempotent, "credits": settled_order.credits})


@router.post("/mock-pay", response_model=APIResp)
def mock_pay(
    req: MockPayReq,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(db_dep),
) -> APIResp:
    payment_cfg = load_payment_config(db)
    if not bool(payment_cfg.get("test_mode", settings.payment_test_mode)):
        raise BizError(code=4213, message="当前环境未开启测试支付")
    order_no = make_order_no()
    try:
        order, idempotent = _settle_package_order(
            db,
            user=user,
            package_name=req.package_name,
            order_no=order_no,
            provider="mock",
            source=get_client_source(request),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    _trigger_referral_reward(order, idempotent=idempotent)
    logger.info(
        "billing_mock_pay_paid",
        extra={"order_no": order_no, "user_id": user.id, "idempotent": idempotent},
    )
    return ok(data={"order_no": order_no, "status": "paid", "credits": order.credits, "idempotent": idempotent})


@router.post("/callback", response_model=APIResp)
def pay_callback(req: PayCallbackReq, request: Request, db: Session = Depends(db_dep)) -> APIResp:
    payload = req.model_dump(exclude={"sign"})
    if not verify_payload_signature(payload, req.sign, db=db):
        raise BizError(code=4204, message="支付回调验签失败")

    now_ts = int(datetime.now(timezone.utc).timestamp())
    if abs(now_ts - req.paid_at) > settings.payment_callback_ttl_seconds:
        raise BizError(code=4205, message="支付回调已过期")
    if req.status != "paid":
        raise BizError(code=4206, message="仅支持 paid 状态回调")

    user = db.get(User, req.user_id)
    if user is None:
        raise BizError(code=4040, message="用户不存在", http_status=404)

    try:
        order, idempotent = _settle_package_order(
            db,
            user=user,
            package_name=req.package_name,
            order_no=req.order_no,
            provider=req.provider,
            amount_cny=req.amount_cny,
            source=get_client_source(request, default=SYSTEM_CLIENT_SOURCE),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    _trigger_referral_reward(order, idempotent=idempotent)
    logger.info(
        "billing_callback_paid",
        extra={
            "order_no": order.order_no,
            "user_id": user.id,
            "provider": req.provider,
            "idempotent": idempotent,
        },
    )

    return ok(
        data={
            "order_no": order.order_no,
            "status": order.status,
            "credits": order.credits,
            "idempotent": idempotent,
        }
    )


@router.post("/notify/wechatpay")
async def wechatpay_notify(request: Request, db: Session = Depends(db_dep)) -> JSONResponse:
    try:
        body = await request.body()
        result = parse_wechatpay_notify(db, body=body, headers=request.headers)
        if result["status"] == "paid":
            try:
                order, idempotent = _settle_existing_order(
                    db,
                    order_no=result["order_no"],
                    provider="wechat",
                    amount_cny=result.get("amount_cny"),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            _trigger_referral_reward(order, idempotent=idempotent)
        elif result["status"] == "closed":
            order = db.query(Order).filter(Order.order_no == result["order_no"]).with_for_update().first()
            if order and order.status == "created":
                order.status = "closed"
                db.commit()
        return _wechat_ack(True, "成功")
    except BizError as exc:
        logger.warning("billing_wechatpay_notify_failed", extra={"detail": exc.message})
        return _wechat_ack(False, exc.message)
    except Exception as exc:
        logger.exception("billing_wechatpay_notify_exception")
        return _wechat_ack(False, str(exc)[:120] or "回调处理失败")


@router.post("/notify/alipay")
async def alipay_notify(request: Request, db: Session = Depends(db_dep)) -> PlainTextResponse:
    try:
        form = await request.form()
        result = parse_alipay_notify(form, db)
        if result["status"] == "paid":
            try:
                order, idempotent = _settle_existing_order(
                    db,
                    order_no=result["order_no"],
                    provider="alipay",
                    amount_cny=result.get("amount_cny"),
                )
                db.commit()
            except Exception:
                db.rollback()
                raise
            _trigger_referral_reward(order, idempotent=idempotent)
        elif result["status"] == "closed":
            order = db.query(Order).filter(Order.order_no == result["order_no"]).with_for_update().first()
            if order and order.status == "created":
                order.status = "closed"
                db.commit()
        return PlainTextResponse("success")
    except Exception as exc:
        logger.warning("billing_alipay_notify_failed", extra={"detail": str(exc)[:160]})
        return PlainTextResponse("failure", status_code=400)
