from datetime import datetime
import logging
from pathlib import Path
import time
import uuid

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.api.router import api_router
from app.config import get_settings
from app.database import Base, engine
from app.exceptions import BizError
from app.logging_setup import setup_logging
from app.models import AdminUser
from app.responses import fail, ok
from app.security import hash_password

setup_logging()
logger = logging.getLogger("app.main")
settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(BizError)
async def biz_error_handler(_: Request, exc: BizError) -> JSONResponse:
    return JSONResponse(status_code=exc.http_status, content=fail(exc.code, exc.message).model_dump())


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=fail(1001, "参数校验失败", data={"errors": exc.errors()}).model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
    code = exc.status_code
    msg = exc.detail if isinstance(exc.detail, str) else "请求失败"
    return JSONResponse(status_code=exc.status_code, content=fail(code, msg).model_dump())


@app.exception_handler(Exception)
async def unknown_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled_exception",
        extra={
            "method": request.method,
            "path": request.url.path,
        },
    )
    return JSONResponse(
        status_code=500,
        content=fail(5000, "服务器内部错误").model_dump(),
    )


@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", "").strip() or uuid.uuid4().hex[:16]
    start = time.perf_counter()
    status_code = 500
    response = None
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        client_ip = request.client.host if request.client else ""
        logger.info(
            "http_request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "elapsed_ms": elapsed_ms,
                "client_ip": client_ip,
            },
        )
        if response is not None:
            response.headers["x-request-id"] = request_id


def init_super_admin() -> None:
    from sqlalchemy.orm import Session

    with Session(engine) as db:
        row = db.query(AdminUser).filter(AdminUser.username == settings.admin_init_username).first()
        if row:
            return
        db.add(
            AdminUser(
                username=settings.admin_init_username,
                password_hash=hash_password(settings.admin_init_password),
                role="super_admin",
                last_login=datetime.utcnow(),
            )
        )
        db.commit()


def assert_production_secrets() -> None:
    if settings.app_env != "prod":
        return
    weak_items = []
    if settings.jwt_secret == "change_me_in_prod":
        weak_items.append("JWT_SECRET")
    if settings.payment_sign_secret == "change_me_payment_sign_key":
        weak_items.append("PAYMENT_SIGN_SECRET")
    if settings.admin_init_password == "admin123456":
        weak_items.append("ADMIN_INIT_PASSWORD")
    if weak_items:
        joined = ", ".join(weak_items)
        raise RuntimeError(f"生产环境密钥未配置安全值: {joined}")


def run_migrations() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    alembic_ini = base_dir / "alembic.ini"
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("script_location", str(base_dir / "alembic"))
    try:
        command.upgrade(cfg, "head")
    except OperationalError as exc:
        msg = str(exc).lower()
        if "already exists" not in msg:
            raise
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        has_legacy_tables = "admin_users" in tables
        has_alembic_version = "alembic_version" in tables
        alembic_version_empty = False
        if has_alembic_version:
            with engine.connect() as conn:
                rows = conn.execute(text("select version_num from alembic_version limit 1")).fetchall()
                alembic_version_empty = len(rows) == 0
        if not (has_legacy_tables and (not has_alembic_version or alembic_version_empty)):
            raise
        logger.warning("legacy_schema_detected_auto_stamp_head")
        command.stamp(cfg, "head")


def repair_missing_tables() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    expected_tables = set(Base.metadata.tables.keys())
    missing_tables = sorted(expected_tables - existing_tables)
    if not missing_tables:
        return
    Base.metadata.create_all(
        bind=engine,
        tables=[Base.metadata.tables[name] for name in missing_tables],
        checkfirst=True,
    )
    logger.warning(
        "schema_repair_created_missing_tables",
        extra={"tables": missing_tables},
    )


@app.on_event("startup")
def on_startup() -> None:
    assert_production_secrets()
    run_migrations()
    repair_missing_tables()
    init_super_admin()
    logger.info("startup_completed", extra={"app_env": settings.app_env})


@app.get("/health")
def health() -> dict:
    return ok(data={"status": "ok"}).model_dump()


app.include_router(api_router, prefix="/api/v1")

