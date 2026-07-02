import re
import uuid
from datetime import time

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.health_centre import CentreStatus, CentreType

PHONE_REGEX = re.compile(r"^\+?\d{7,15}$")


def _validate_latitude(value: float | None) -> float | None:
    if value is not None and not (-90 <= value <= 90):
        raise ValueError("latitude must be between -90 and 90")
    return value


def _validate_longitude(value: float | None) -> float | None:
    if value is not None and not (-180 <= value <= 180):
        raise ValueError("longitude must be between -180 and 180")
    return value


def _validate_phone(value: str | None) -> str | None:
    if value is not None and not PHONE_REGEX.match(value):
        raise ValueError("phone must contain 7-15 digits with an optional leading '+'")
    return value


class HealthCentreBase(BaseModel):
    name: str
    type: CentreType
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    phone: str | None = None
    email: str | None = None
    opening_time: time | None = None
    closing_time: time | None = None

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: float | None) -> float | None:
        return _validate_latitude(value)

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: float | None) -> float | None:
        return _validate_longitude(value)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        return _validate_phone(value)


class HealthCentreCreate(HealthCentreBase):
    district_id: uuid.UUID
    block_id: uuid.UUID | None = None
    village_id: uuid.UUID | None = None


class HealthCentreUpdate(BaseModel):
    name: str | None = None
    type: CentreType | None = None
    block_id: uuid.UUID | None = None
    village_id: uuid.UUID | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    phone: str | None = None
    email: str | None = None
    opening_time: time | None = None
    closing_time: time | None = None
    status: CentreStatus | None = None

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: float | None) -> float | None:
        return _validate_latitude(value)

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: float | None) -> float | None:
        return _validate_longitude(value)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        return _validate_phone(value)


class HealthCentreRead(HealthCentreBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    district_id: uuid.UUID
    block_id: uuid.UUID | None
    village_id: uuid.UUID | None
    status: CentreStatus


class HealthCentreNearbyRead(HealthCentreRead):
    distance_km: float
