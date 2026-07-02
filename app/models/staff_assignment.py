import uuid
from datetime import date
from enum import Enum

from sqlalchemy import Date, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AssignmentStatus(str, Enum):
    ACTIVE = "active"
    TRANSFERRED = "transferred"
    INACTIVE = "inactive"


class StaffAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "staff_assignments"
    __table_args__ = (
        Index(
            "ux_staff_assignments_one_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    health_centre_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("health_centres.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    designation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    joined_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[AssignmentStatus] = mapped_column(
        String(20), nullable=False, default=AssignmentStatus.ACTIVE
    )
