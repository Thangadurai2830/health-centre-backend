from enum import Enum

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DepartmentStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Department(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "departments"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[DepartmentStatus] = mapped_column(
        String(20), nullable=False, default=DepartmentStatus.ACTIVE
    )
