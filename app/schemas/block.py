import uuid

from pydantic import BaseModel, ConfigDict


class BlockBase(BaseModel):
    name: str
    code: str


class BlockCreate(BlockBase):
    district_id: uuid.UUID


class BlockUpdate(BaseModel):
    name: str | None = None
    code: str | None = None


class BlockRead(BlockBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    district_id: uuid.UUID
