import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, Index, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from database import Base

def utc_now():
    return datetime.now(timezone.utc)

class RiskProbabilityRow(Base):
    __tablename__ = "risk_probability_rows"
    __table_args__ = (
        UniqueConstraint("matrix_version", "zinc_group", "upsa_group", "clinical_filter", name="uq_risk_probability_row"),
        Index("ix_risk_probability_lookup", "matrix_version", "zinc_group", "upsa_group", "clinical_filter"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    matrix_version: Mapped[str] = mapped_column(String(80), index=True)
    zinc_group: Mapped[str] = mapped_column(String(10), index=True)
    upsa_group: Mapped[str] = mapped_column(String(10), index=True)
    clinical_filter: Mapped[str] = mapped_column(String(40), index=True)
    clinical_filter_label: Mapped[str] = mapped_column(String(160))
    n_subjects: Mapped[int] = mapped_column(Integer, default=0)
    events_any: Mapped[int] = mapped_column(Integer, default=0)
    events_ge_3_4: Mapped[int] = mapped_column(Integer, default=0)
    events_ge_4_3: Mapped[int] = mapped_column(Integer, default=0)
    raw_any: Mapped[float | None] = mapped_column(Float)
    raw_ge_3_4: Mapped[float | None] = mapped_column(Float)
    raw_ge_4_3: Mapped[float | None] = mapped_column(Float)
    adjusted_any: Mapped[float | None] = mapped_column(Float)
    adjusted_ge_3_4: Mapped[float | None] = mapped_column(Float)
    adjusted_ge_4_3: Mapped[float | None] = mapped_column(Float)
    stability_note: Mapped[str | None] = mapped_column(String(120))
    method: Mapped[str] = mapped_column(String(180), default="Jeffreys posterior mean (k+0.5)/(n+1)")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
