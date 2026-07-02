import uuid

from pydantic import BaseModel, ConfigDict


class WardBase(BaseModel):
    name: str
    type: str | None = None
    capacity: int = 0


class WardCreate(WardBase):
    health_centre_id: uuid.UUID
    department_id: uuid.UUID


class WardUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    capacity: int | None = None
    department_id: uuid.UUID | None = None


class WardRead(WardBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    health_centre_id: uuid.UUID
    department_id: uuid.UUID
