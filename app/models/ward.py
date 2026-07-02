import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Ward(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "wards"
    __table_args__ = (
        UniqueConstraint("health_centre_id", "name", name="uq_wards_health_centre_id_name"),
    )

    health_centre_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("health_centres.id", ondelete="CASCADE"), nullable=False, index=True
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
