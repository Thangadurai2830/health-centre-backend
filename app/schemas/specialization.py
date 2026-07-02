import uuid

from pydantic import BaseModel, ConfigDict


class SpecializationBase(BaseModel):
    name: str
    description: str | None = None


class SpecializationCreate(SpecializationBase):
    pass


class SpecializationUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class SpecializationRead(SpecializationBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
