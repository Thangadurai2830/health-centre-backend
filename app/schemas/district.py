import uuid

from pydantic import BaseModel, ConfigDict

from app.models.district import DistrictStatus


class DistrictBase(BaseModel):
    name: str
    state: str
    code: str


class DistrictCreate(DistrictBase):
    pass


class DistrictUpdate(BaseModel):
    name: str | None = None
    state: str | None = None
    code: str | None = None
    status: DistrictStatus | None = None


class DistrictRead(DistrictBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: DistrictStatus
