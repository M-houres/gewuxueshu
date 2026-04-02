from app.schemas import APIResp


def ok(data: object | None = None, message: str = "success") -> APIResp:
    return APIResp(code=0, data=data, message=message)


def fail(code: int, message: str, data: object | None = None) -> APIResp:
    return APIResp(code=code, data=data, message=message)
