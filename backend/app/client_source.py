from fastapi import Request

DEFAULT_CLIENT_SOURCE = "web"
SYSTEM_CLIENT_SOURCE = "system"
ADMIN_CLIENT_SOURCE = "admin"
MINIPROGRAM_CLIENT_SOURCE = "miniprogram"

_CLIENT_SOURCE_ALIASES = {
    "web": DEFAULT_CLIENT_SOURCE,
    "h5": DEFAULT_CLIENT_SOURCE,
    "site": DEFAULT_CLIENT_SOURCE,
    "mini_program": MINIPROGRAM_CLIENT_SOURCE,
    "miniprogram": MINIPROGRAM_CLIENT_SOURCE,
    "wxapp": MINIPROGRAM_CLIENT_SOURCE,
    "wechat_miniprogram": MINIPROGRAM_CLIENT_SOURCE,
    "wechat_mini_program": MINIPROGRAM_CLIENT_SOURCE,
    "admin": ADMIN_CLIENT_SOURCE,
    "system": SYSTEM_CLIENT_SOURCE,
}


def normalize_client_source(raw: str | None, *, default: str = DEFAULT_CLIENT_SOURCE) -> str:
    value = str(raw or "").strip().lower().replace("-", "_")
    if not value:
        return default
    return _CLIENT_SOURCE_ALIASES.get(value, default)


def get_client_source(request: Request, *, default: str = DEFAULT_CLIENT_SOURCE) -> str:
    return normalize_client_source(request.headers.get("x-client-source"), default=default)
