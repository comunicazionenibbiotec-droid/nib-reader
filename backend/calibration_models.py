import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CalibrationSession(Base):
    __tablename__ = "calibration_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    calibration_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    analyte: Mapped[str] = mapped_column(String(20), default="upsa", index=True)
    lot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("qms_lots.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    lot = relationship("QmsLot")
