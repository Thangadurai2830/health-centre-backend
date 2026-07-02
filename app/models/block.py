import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Block(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "blocks"
    __table_args__ = (UniqueConstraint("district_id", "code", name="uq_blocks_district_id_code"),)

    district_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("districts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
