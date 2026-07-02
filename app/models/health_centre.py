import uuid
from datetime import time
from enum import Enum

from sqlalchemy import Float, ForeignKey, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CentreType(str, Enum):
    PHC = "PHC"
    CHC = "CHC"
    SUB_CENTRE = "SubCentre"
    DISTRICT_HOSPITAL = "DistrictHospital"
    MEDICAL_COLLEGE = "MedicalCollege"


class CentreStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FLAGGED = "flagged"


class HealthCentre(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "health_centres"
    __table_args__ = (
        UniqueConstraint("district_id", "name", name="uq_health_centres_district_id_name"),
    )

    district_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("districts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    block_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("blocks.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    village_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("villages.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[CentreType] = mapped_column(String(30), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    opening_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    closing_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    status: Mapped[CentreStatus] = mapped_column(
        String(20), nullable=False, default=CentreStatus.ACTIVE
    )
