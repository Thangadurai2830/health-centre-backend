from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(str, Enum):
    CITIZEN = "citizen"
    RECEPTION_STAFF = "reception_staff"
    DOCTOR = "doctor"
    PHARMACIST = "pharmacist"
    DISTRICT_ADMIN = "district_admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    mobile_number: Mapped[str] = mapped_column(
        String(15), nullable=False, unique=True, index=True
    )
    country_code: Mapped[str] = mapped_column(String(5), nullable=False, default="+91")
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    role: Mapped[UserRole] = mapped_column(String(20), nullable=False, default=UserRole.CITIZEN)
    status: Mapped[UserStatus] = mapped_column(
        String(20), nullable=False, default=UserStatus.ACTIVE
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
