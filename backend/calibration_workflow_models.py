import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from database import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


def utc_now():
    return datetime.now(timezone.utc)


class CalibrationPlan(Base):
    __tablename__ = "calibration_plans"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("calibration_sessions.id", ondelete="CASCADE"), unique=True, index=True
    )
    expected_concentrations: Mapped[int] = mapped_column(Integer)
    default_replicates: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class CalibrationPoint(Base):
    __tablename__ = "calibration_points"
    __table_args__ = (
        UniqueConstraint("session_id", "optical_score", "concentration_slot", name="uq_cal_point_slot"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("calibration_sessions.id", ondelete="CASCADE"), index=True
    )
    optical_score: Mapped[int] = mapped_column(Integer, index=True)
    concentration_slot: Mapped[str] = mapped_column(String(1))
    instrumental_concentration: Mapped[float] = mapped_column(Float, index=True)
    concentration_unit: Mapped[str] = mapped_column(String(20), default="ug/mL")
    concentration_normalized_ng_ml: Mapped[float] = mapped_column(Float, index=True)
    planned_replicates: Mapped[int] = mapped_column(Integer, default=1)
    completed_replicates: Mapped[int] = mapped_column(Integer, default=0)
    skipped_replicates: Mapped[int] = mapped_column(Integer, default=0)
    acquisition_mode: Mapped[str] = mapped_column(String(20), default="READER")
    status: Mapped[str] = mapped_column(String(20), default="IN_PROGRESS", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class CalibrationMeasurement(Base):
    __tablename__ = "calibration_measurements"
    __table_args__ = (
        UniqueConstraint("point_id", "replicate_number", name="uq_cal_measure_rep"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("calibration_points.id", ondelete="CASCADE"), index=True
    )
    record_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    replicate_number: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(20), default="READER")
    status: Mapped[str] = mapped_column(String(20), default="COMPLETED")
    skip_reason: Mapped[str | None] = mapped_column(String(200))

    # uPSA metrics, retained unchanged.
    t_height: Mapped[float | None] = mapped_column(Float)
    t_area: Mapped[float | None] = mapped_column(Float)
    t_width: Mapped[float | None] = mapped_column(Float)
    t_fwhm: Mapped[float | None] = mapped_column(Float)
    c_height: Mapped[float | None] = mapped_column(Float)
    c_area: Mapped[float | None] = mapped_column(Float)
    c_width: Mapped[float | None] = mapped_column(Float)
    c_fwhm: Mapped[float | None] = mapped_column(Float)
    height_ratio: Mapped[float | None] = mapped_column(Float)
    area_ratio: Mapped[float | None] = mapped_column(Float)

    # uZinc structured metrics.
    lab_l: Mapped[float | None] = mapped_column(Float)
    lab_a: Mapped[float | None] = mapped_column(Float, index=True)
    lab_b: Mapped[float | None] = mapped_column(Float, index=True)
    hue_lab: Mapped[float | None] = mapped_column(Float, index=True)
    chroma: Mapped[float | None] = mapped_column(Float)
    a_over_b: Mapped[float | None] = mapped_column(Float, index=True)
    saturation: Mapped[float | None] = mapped_column(Float)
    r_over_g: Mapped[float | None] = mapped_column(Float)
    b_over_g: Mapped[float | None] = mapped_column(Float)
    magenta_index: Mapped[float | None] = mapped_column(Float, index=True)
    delta_e_white: Mapped[float | None] = mapped_column(Float)
    luminance_ratio: Mapped[float | None] = mapped_column(Float)

    # uZinc analytical QC.
    white_luminance_cv: Mapped[float | None] = mapped_column(Float)
    white_overexposed_fraction: Mapped[float | None] = mapped_column(Float)
    sample_clipped_fraction: Mapped[float | None] = mapped_column(Float)
    white_clipped_fraction: Mapped[float | None] = mapped_column(Float)
    sample_pixel_count: Mapped[int | None] = mapped_column(Integer)
    white_pixel_count: Mapped[int | None] = mapped_column(Integer)
    disc_detected: Mapped[bool | None] = mapped_column(Boolean)
    detection_method: Mapped[str | None] = mapped_column(String(80))
    uzinc_qc_status: Mapped[str | None] = mapped_column(String(30), index=True)

    # Full analytical payload is preserved for traceability and reanalysis.
    raw_measurement: Mapped[dict] = mapped_column(JSON_TYPE, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
