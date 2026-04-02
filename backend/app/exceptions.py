from fastapi import status


class BizError(Exception):
    def __init__(self, code: int, message: str, http_status: int = status.HTTP_400_BAD_REQUEST) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)
