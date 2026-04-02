from collections.abc import Generator
from pathlib import Path
from types import SimpleNamespace
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.database import Base
from app.deps import current_admin, db_dep, get_redis
from app.main import app


class FakeRedis:
    def __init__(self) -> None:
        self._values: dict[str, str] = {}
        self._exp_at: dict[str, float] = {}

    def _purge_if_expired(self, key: str) -> None:
        exp = self._exp_at.get(key)
        if exp is None:
            return
        if exp <= time.time():
            self._values.pop(key, None)
            self._exp_at.pop(key, None)

    def setex(self, key: str, seconds: int, value) -> bool:
        self._values[key] = str(value)
        self._exp_at[key] = time.time() + int(seconds)
        return True

    def get(self, key: str):
        self._purge_if_expired(key)
        return self._values.get(key)

    def ttl(self, key: str) -> int:
        self._purge_if_expired(key)
        if key not in self._values:
            return -2
        exp = self._exp_at.get(key)
        if exp is None:
            return -1
        remain = int(exp - time.time())
        if remain <= 0:
            self._values.pop(key, None)
            self._exp_at.pop(key, None)
            return -2
        return remain

    def incr(self, key: str) -> int:
        self._purge_if_expired(key)
        current = self._values.get(key, "0")
        try:
            value = int(current)
        except Exception:
            value = 0
        value += 1
        self._values[key] = str(value)
        return value

    def expire(self, key: str, seconds: int) -> bool:
        self._purge_if_expired(key)
        if key not in self._values:
            return False
        self._exp_at[key] = time.time() + int(seconds)
        return True

    def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            self._purge_if_expired(key)
            if key in self._values:
                removed += 1
                self._values.pop(key, None)
            self._exp_at.pop(key, None)
        return removed


@pytest.fixture()
def db_session(tmp_path: Path) -> Generator[Session, None, None]:
    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False}, future=True)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_db() -> Generator[Session, None, None]:
        yield db_session

    fake_redis = FakeRedis()
    settings = get_settings()
    old_auth_debug = settings.auth_return_debug_code
    settings.auth_return_debug_code = True

    startup_handlers = list(app.router.on_startup)
    shutdown_handlers = list(app.router.on_shutdown)
    app.router.on_startup.clear()
    app.router.on_shutdown.clear()

    app.dependency_overrides[db_dep] = override_db
    app.dependency_overrides[get_redis] = lambda: fake_redis
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()
    settings.auth_return_debug_code = old_auth_debug

    app.router.on_startup.extend(startup_handlers)
    app.router.on_shutdown.extend(shutdown_handlers)


@pytest.fixture()
def admin_override() -> Generator[None, None, None]:
    app.dependency_overrides[current_admin] = lambda: SimpleNamespace(id=1, username="admin", role="super_admin")
    try:
        yield
    finally:
        app.dependency_overrides.pop(current_admin, None)


@pytest.fixture()
def settings_override(tmp_path: Path) -> Generator[None, None, None]:
    settings = get_settings()
    old_secret = settings.payment_sign_secret
    old_ttl = settings.payment_callback_ttl_seconds
    old_algo_root = settings.algorithm_package_root
    old_algo_max_mb = settings.algorithm_package_max_mb
    old_algo_exec_timeout = settings.algorithm_package_exec_timeout_seconds

    settings.payment_sign_secret = "test_sign_secret"
    settings.payment_callback_ttl_seconds = 1200
    settings.algorithm_package_root = str(tmp_path / "algorithm_packages")
    settings.algorithm_package_max_mb = 20
    settings.algorithm_package_exec_timeout_seconds = 8
    try:
        yield
    finally:
        settings.payment_sign_secret = old_secret
        settings.payment_callback_ttl_seconds = old_ttl
        settings.algorithm_package_root = old_algo_root
        settings.algorithm_package_max_mb = old_algo_max_mb
        settings.algorithm_package_exec_timeout_seconds = old_algo_exec_timeout
