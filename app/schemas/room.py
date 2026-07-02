import uuid

from pydantic import BaseModel, ConfigDict

from app.models.room import RoomStatus


class RoomBase(BaseModel):
    room_number: str
    floor: str | None = None


class RoomCreate(RoomBase):
    ward_id: uuid.UUID


class RoomUpdate(BaseModel):
    room_number: str | None = None
    floor: str | None = None
    status: RoomStatus | None = None


class RoomRead(RoomBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ward_id: uuid.UUID
    status: RoomStatus
