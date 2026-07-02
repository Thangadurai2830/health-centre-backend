import uuid
from enum import Enum

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RoomStatus(str, Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"


class Room(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint("ward_id", "room_number", name="uq_rooms_ward_id_room_number"),
    )

    ward_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    room_number: Mapped[str] = mapped_column(String(50), nullable=False)
    floor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[RoomStatus] = mapped_column(
        String(20), nullable=False, default=RoomStatus.AVAILABLE
    )
