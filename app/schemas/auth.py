import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.user import UserProfileRead

MOBILE_REGEX = re.compile(r"^[6-9]\d{9}$")
COUNTRY_CODE_REGEX = re.compile(r"^\+\d{1,4}$")


class SendOtpRequest(BaseModel):
    mobile_number: str = Field(examples=["9876543210"])
    country_code: str = Field(default="+91", examples=["+91"])

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile_number(cls, value: str) -> str:
        if not MOBILE_REGEX.match(value):
            raise ValueError("mobile_number must be a 10-digit number starting with 6-9")
        return value

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, value: str) -> str:
        if not COUNTRY_CODE_REGEX.match(value):
            raise ValueError("country_code must be in the form '+<1-4 digits>'")
        return value


class SendOtpResponse(BaseModel):
    message: str = Field(examples=["OTP sent successfully"])
    mobile_number: str = Field(examples=["9876543210"])
    expires_in_seconds: int = Field(examples=[300])
    resend_allowed_in_seconds: int = Field(examples=[60])


class DeviceInfo(BaseModel):
    device_name: str | None = None
    device_type: str | None = None
    device_os: str | None = None
    browser: str | None = None


class VerifyOtpRequest(BaseModel):
    mobile_number: str = Field(examples=["9876543210"])
    country_code: str = Field(default="+91", examples=["+91"])
    otp_code: str = Field(examples=["123456"])
    device: DeviceInfo | None = None

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile_number(cls, value: str) -> str:
        if not MOBILE_REGEX.match(value):
            raise ValueError("mobile_number must be a 10-digit number starting with 6-9")
        return value

    @field_validator("otp_code")
    @classmethod
    def validate_otp_code(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 6:
            raise ValueError("otp_code must be a 6-digit numeric code")
        return value


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(examples=[86400])
    is_new_user: bool
    user: UserProfileRead


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(examples=[86400])


class LogoutRequest(BaseModel):
    refresh_token: str


class CheckMobileResponse(BaseModel):
    exists: bool
    is_verified: bool = False


class SessionRead(BaseModel):
    id: uuid.UUID
    device_name: str | None
    device_type: str | None
    device_os: str | None
    browser: str | None
    ip_address: str | None
    location: str | None
    login_time: datetime
    last_activity: datetime
    status: str
    is_current: bool = False
