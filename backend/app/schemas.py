from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class APIResp(BaseModel):
    code: int = 0
    message: str = "success"
    data: Any | None = None


class SendCodeReq(BaseModel):
    phone: str = Field(min_length=11, max_length=20)


class LoginReq(BaseModel):
    phone: str = Field(min_length=11, max_length=20)
    code: str = Field(min_length=4, max_length=8)
    referrer_code: str | None = None
    device_fingerprint: str | None = Field(default=None, max_length=128)


class UserResp(BaseModel):
    id: int
    phone: str
    nickname: str
    credits: int
    created_at: datetime


class TaskCreateResp(BaseModel):
    id: int
    status: str
    cost_credits: int


class AdminLoginReq(BaseModel):
    username: str
    password: str


class AdminAdjustCreditReq(BaseModel):
    delta: int
    reason: str


class PaginationQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class MockPayReq(BaseModel):
    package_name: str


class CreateOrderReq(BaseModel):
    package_name: str
    provider: str = Field(default="wechat")


class PayCallbackReq(BaseModel):
    order_no: str = Field(min_length=8, max_length=64)
    user_id: int = Field(ge=1)
    package_name: str
    amount_cny: float = Field(gt=0)
    paid_at: int = Field(ge=1)
    status: str = Field(default="paid")
    provider: str = Field(default="wechat")
    nonce: str = Field(min_length=4, max_length=64)
    sign: str = Field(min_length=32, max_length=128)


class AlgoPackageActivateReq(BaseModel):
    platform: str = Field(min_length=2, max_length=32)
    function_type: str = Field(min_length=2, max_length=32)
    version: str = Field(min_length=3, max_length=64)


class AlgoPackageUploadReq(BaseModel):
    platform: str = Field(min_length=2, max_length=32)
    function_type: str = Field(min_length=2, max_length=32)


class ReferralConfigReq(BaseModel):
    register_inviter_credits: int = Field(ge=0, le=100000)
    register_invitee_bonus: int = Field(ge=0, le=100000)
    first_pay_ratio: float = Field(ge=0.0, le=1.0)
    recurring_ratio: float = Field(ge=0.0, le=1.0)
    ip_limit_24h: int = Field(ge=1, le=100)
