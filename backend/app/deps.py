from typing import Callable, Generator
import time

import redis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.client_source import get_client_source
from app.config import get_settings
from app.database import get_db
from app.models import AdminUser, User
from app.security import decode_token

settings = get_settings()
redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    decode_responses=True,
)


class MemoryRedisCompat:
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

    def ping(self) -> bool:
        return True

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


memory_redis = MemoryRedisCompat()

auth_scheme = HTTPBearer(auto_error=False)
LEGACY_OPERATOR_DEFAULT_PERMISSIONS = {
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


def get_redis():
    try:
        redis_client.ping()
        return redis_client
    except redis.RedisError:
        return memory_redis


def client_source_dep(request: Request) -> str:
    return get_client_source(request)


def db_dep() -> Generator[Session, None, None]:
    yield from get_db()


def current_user(
    cred: HTTPAuthorizationCredentials = Depends(auth_scheme),
    db: Session = Depends(db_dep),
) -> User:
    if cred is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing token")
    try:
        payload = decode_token(cred.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token") from exc
    if payload.get("scope") != "user":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid scope")
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")
    return user


def current_admin(
    cred: HTTPAuthorizationCredentials = Depends(auth_scheme),
    db: Session = Depends(db_dep),
) -> AdminUser:
    if cred is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing token")
    try:
        payload = decode_token(cred.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token") from exc
    if payload.get("scope") != "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid scope")
    admin = db.get(AdminUser, int(payload["sub"]))
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="admin not found")
    if not getattr(admin, "is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin disabled")
    return admin


def current_super_admin(admin: AdminUser = Depends(current_admin)) -> AdminUser:
    if admin.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return admin


def normalize_admin_permissions(value) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, (list, tuple, set)):
        return {str(item).strip() for item in value if str(item).strip()}
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return set()
        return {part.strip() for part in raw.split(",") if part.strip()}
    return set()


def admin_has_permission(admin: AdminUser, permission: str) -> bool:
    if not permission:
        return True
    if admin.role == "super_admin":
        return True
    permissions = normalize_admin_permissions(getattr(admin, "permissions_json", []))
    if not permissions:
        permissions = set(LEGACY_OPERATOR_DEFAULT_PERMISSIONS)
    if "*" in permissions:
        return True
    if permission in permissions:
        return True
    if ":" in permission:
        scope = permission.split(":", 1)[0]
        if f"{scope}:*" in permissions:
            return True
    return False


def require_admin_permission(permission: str) -> Callable[[AdminUser], AdminUser]:
    def _dep(admin: AdminUser = Depends(current_admin)) -> AdminUser:
        if admin_has_permission(admin, permission):
            return admin
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    return _dep
