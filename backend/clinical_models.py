import uuid
from datetime import date, datetime, timezone
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from database import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")
def utc_now(): return datetime.now(timezone.utc)

class ClinicalPatient(Base):
    __tablename__ = "clinical_patients"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    birth_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class ClinicalCase(Base):
    __tablename__ = "clinical_cases"
    __table_args__ = (Index("ix_clinical_cases_patient_pathway", "patient_id", "clinical_pathway"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinical_patients.id", ondelete="CASCADE"), index=True)
    clinical_pathway: Mapped[str] = mapped_column(String(40), index=True)
    recruitment_center: Mapped[str | None] = mapped_column(String(120), index=True)
    diagnosis_date: Mapped[date | None] = mapped_column(Date, index=True)
    initial_diagnosis: Mapped[str | None] = mapped_column(String(60), index=True)
    initial_gleason_primary: Mapped[int | None] = mapped_column(Integer)
    initial_gleason_secondary: Mapped[int | None] = mapped_column(Integer)
    initial_isup_grade_group: Mapped[int | None] = mapped_column(Integer)
    initial_stage: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default="OPEN", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class ClinicalVisit(Base):
    __tablename__ = "clinical_visits"
    __table_args__ = (UniqueConstraint("case_id", "visit_code", name="uq_clinical_visit_code"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinical_cases.id", ondelete="CASCADE"), index=True)
    record_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("test_records.id", ondelete="SET NULL"), index=True)
    visit_code: Mapped[str] = mapped_column(String(40))
    visit_date: Mapped[date] = mapped_column(Date, index=True)
    timepoint_months: Mapped[float | None] = mapped_column(Float)
    serum_psa_ng_ml: Mapped[float | None] = mapped_column(Float)
    prostate_volume_ml: Mapped[float | None] = mapped_column(Float)
    psa_density: Mapped[float | None] = mapped_column(Float)
    dre_result: Mapped[str | None] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class MriOutcome(Base):
    __tablename__ = "mri_outcomes"
    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinical_visits.id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[str] = mapped_column(String(30), default="UNKNOWN", index=True)
    mri_date: Mapped[date | None] = mapped_column(Date, index=True)
    pirads_score: Mapped[int | None] = mapped_column(Integer, index=True)
    suspicious_lesion: Mapped[bool | None] = mapped_column(Boolean)
    lesion_count: Mapped[int | None] = mapped_column(Integer)
    index_lesion_size_mm: Mapped[float | None] = mapped_column(Float)
    index_lesion_location: Mapped[str | None] = mapped_column(String(160))
    prostate_volume_ml: Mapped[float | None] = mapped_column(Float)
    possible_benign_mimic: Mapped[bool] = mapped_column(Boolean, default=False)
    benign_mimic_type: Mapped[str | None] = mapped_column(String(50))
    benign_mimic_notes: Mapped[str | None] = mapped_column(Text)
    report_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    report_source: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class BiopsyOutcome(Base):
    __tablename__ = "biopsy_outcomes"
    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinical_visits.id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[str] = mapped_column(String(30), default="UNKNOWN", index=True)
    biopsy_date: Mapped[date | None] = mapped_column(Date, index=True)
    non_performance_reason: Mapped[str | None] = mapped_column(String(200))
    result: Mapped[str | None] = mapped_column(String(50), index=True)
    gleason_primary: Mapped[int | None] = mapped_column(Integer)
    gleason_secondary: Mapped[int | None] = mapped_column(Integer)
    gleason_total: Mapped[int | None] = mapped_column(Integer)
    isup_grade_group: Mapped[int | None] = mapped_column(Integer, index=True)
    positive_cores: Mapped[int | None] = mapped_column(Integer)
    total_cores: Mapped[int | None] = mapped_column(Integer)
    max_core_involvement_percent: Mapped[float | None] = mapped_column(Float)
    any_pca: Mapped[bool | None] = mapped_column(Boolean)
    clinically_significant_pca: Mapped[bool | None] = mapped_column(Boolean)
    gleason_ge_7: Mapped[bool | None] = mapped_column(Boolean)
    gleason_gt_7: Mapped[bool | None] = mapped_column(Boolean)
    report_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class ProgressionOutcome(Base):
    __tablename__ = "progression_outcomes"
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinical_cases.id", ondelete="CASCADE"), primary_key=True)
    progression_status: Mapped[str] = mapped_column(String(30), default="NOT_EVALUABLE", index=True)
    progression_date: Mapped[date | None] = mapped_column(Date, index=True)
    last_followup_date: Mapped[date | None] = mapped_column(Date, index=True)
    months_diagnosis_to_progression: Mapped[float | None] = mapped_column(Float)
    progression_type: Mapped[dict] = mapped_column(JSON_TYPE, default=dict)
    followup_gleason_primary: Mapped[int | None] = mapped_column(Integer)
    followup_gleason_secondary: Mapped[int | None] = mapped_column(Integer)
    followup_isup_grade_group: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class ModelPrediction(Base):
    __tablename__ = "model_predictions"
    __table_args__ = (Index("ix_model_predictions_case_context", "case_id", "prediction_context"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinical_cases.id", ondelete="CASCADE"), index=True)
    visit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinical_visits.id", ondelete="SET NULL"), index=True)
    prediction_context: Mapped[str] = mapped_column(String(40), index=True)
    model_version: Mapped[str] = mapped_column(String(80), index=True)
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    probabilities: Mapped[dict] = mapped_column(JSON_TYPE)
    input_snapshot: Mapped[dict] = mapped_column(JSON_TYPE)
    quality_flags: Mapped[dict] = mapped_column(JSON_TYPE, default=dict)
    immutable: Mapped[bool] = mapped_column(Boolean, default=True)
