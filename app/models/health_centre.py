import uuid
from enum import Enum

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CentreType(str, Enum):
    PHC = "PHC"
    CHC = "CHC"
    SUB_CENTRE = "SubCentre"


class CentreStatus(str, Enum):
    ACTIVE = "active"
    FLAGGED = "flagged"


class HealthCentre(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "health_centres"

    district_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[CentreType] = mapped_column(String(20), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    catchment_population: Mapped[int] = mapped_column(Integer, default=0)
    bed_capacity: Mapped[int] = mapped_column(Integer, default=0)
    performance_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[CentreStatus] = mapped_column(String(20), default=CentreStatus.ACTIVE)
