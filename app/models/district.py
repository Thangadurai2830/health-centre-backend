from enum import Enum

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DistrictStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class District(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "districts"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    status: Mapped[DistrictStatus] = mapped_column(
        String(20), nullable=False, default=DistrictStatus.ACTIVE
    )
