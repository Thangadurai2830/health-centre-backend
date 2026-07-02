import uuid

from pydantic import BaseModel, ConfigDict, field_validator


class VillageBase(BaseModel):
    name: str
    pincode: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: float | None) -> float | None:
        if value is not None and not (-90 <= value <= 90):
            raise ValueError("latitude must be between -90 and 90")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: float | None) -> float | None:
        if value is not None and not (-180 <= value <= 180):
            raise ValueError("longitude must be between -180 and 180")
        return value


class VillageCreate(VillageBase):
    block_id: uuid.UUID


class VillageUpdate(BaseModel):
    name: str | None = None
    pincode: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: float | None) -> float | None:
        if value is not None and not (-90 <= value <= 90):
            raise ValueError("latitude must be between -90 and 90")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: float | None) -> float | None:
        if value is not None and not (-180 <= value <= 180):
            raise ValueError("longitude must be between -180 and 180")
        return value


class VillageRead(VillageBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    block_id: uuid.UUID
