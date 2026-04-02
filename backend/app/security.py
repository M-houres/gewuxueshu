from datetime import datetime, timedelta, timezone
import hashlib

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()


def _normalize_password(plain: str) -> bytes:
    # 先归一化为固定长度，避免 bcrypt 72 字节限制引发问题
    text = (plain or "").encode("utf-8")
    digest = hashlib.sha256(text).hexdigest()
    return digest.encode("utf-8")


def hash_password(plain: str) -> str:
    normalized = _normalize_password(plain)
    return bcrypt.hashpw(normalized, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    normalized = _normalize_password(plain)
    try:
        encoded_hash = hashed.encode("utf-8")
        if bcrypt.checkpw(normalized, encoded_hash):
            return True
        # 兼容历史密码哈希（旧逻辑直接 bcrypt 原文）
        legacy = (plain or "")[:72].encode("utf-8")
        return bcrypt.checkpw(legacy, encoded_hash)
    except Exception:
        return False


def create_token(subject: str, scope: str, expire_minutes: int | None = None) -> str:
    minutes = expire_minutes or settings.jwt_expire_minutes
    exp = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {"sub": subject, "scope": scope, "exp": exp}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("invalid token") from exc
