import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, Index, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from database import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TestRecord(Base):
    __tablename__ = "test_records"
    __table_args__ = (
        Index("ix_test_records_code_date", "sample_code", "captured_at"),
        Index("ix_test_records_path_diagnosis", "clinical_pathway", "diagnosis"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    base_filename: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    sample_code: Mapped[str] = mapped_column(String(60), index=True)
    progressive_number: Mapped[int | None] = mapped_column(Integer)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    clinical_pathway: Mapped[str | None] = mapped_column(String(40), index=True)
    record_purpose: Mapped[str] = mapped_column(String(30), default="unclassified", index=True)
    study_code: Mapped[str | None] = mapped_column(String(80))
    calibration_code: Mapped[str | None] = mapped_column(String(80), index=True)
    calibration_analyte: Mapped[str | None] = mapped_column(String(20))
    nominal_concentration_ug_ml: Mapped[float | None] = mapped_column(Float)
    replicate_number: Mapped[int | None] = mapped_column(Integer)
    urine_collection_volume_ml: Mapped[float | None] = mapped_column(Float)

    optical_zinc_score_0_4: Mapped[int | None] = mapped_column(Integer)
    optical_psa_score_0_4: Mapped[int | None] = mapped_column(Integer)
    zinc_red_excess: Mapped[float | None] = mapped_column(Float)
    psa_area_t_c_ratio: Mapped[float | None] = mapped_column(Float)
    test_state: Mapped[str | None] = mapped_column(String(50), index=True)
    test_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    lot_id: Mapped[str | None] = mapped_column(String(80), index=True)

    age: Mapped[int | None] = mapped_column(Integer)
    serum_psa_ng_ml: Mapped[float | None] = mapped_column(Float)
    dre_result: Mapped[str | None] = mapped_column(String(40))
    pirads: Mapped[int | None] = mapped_column(Integer)
    prostate_volume_ml: Mapped[float | None] = mapped_column(Float)
    gleason_score: Mapped[str | None] = mapped_column(String(30))
    diagnosis: Mapped[str | None] = mapped_column(String(30), index=True)

    upsa_instrumental_ug_ml: Mapped[float | None] = mapped_column(Float)
    upsa_execution_date: Mapped[date | None] = mapped_column(Date)
    upsa_rapid_frozen: Mapped[bool] = mapped_column(Boolean, default=False)
    upsa_rapid_frozen_date: Mapped[date | None] = mapped_column(Date)
    upsa_instrumental_frozen: Mapped[bool] = mapped_column(Boolean, default=False)
    upsa_instrumental_frozen_date: Mapped[date | None] = mapped_column(Date)

    uzinc_instrumental_ug_ml: Mapped[float | None] = mapped_column(Float)
    uzinc_execution_date: Mapped[date | None] = mapped_column(Date)
    uzinc_rapid_frozen: Mapped[bool] = mapped_column(Boolean, default=False)
    uzinc_rapid_frozen_date: Mapped[date | None] = mapped_column(Date)
    uzinc_instrumental_frozen: Mapped[bool] = mapped_column(Boolean, default=False)
    uzinc_instrumental_frozen_date: Mapped[date | None] = mapped_column(Date)

    raw_record: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
