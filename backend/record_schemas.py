import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Diagnosis = Literal["sano", "prostatite", "BPH", "ISUP1", "ISUP2", "ISUP3", "ISUP4", "ISUP5"]
Pathway = Literal["check_up", "pre_mri", "pre_biopsy", "active_surveillance"]
Gleason = Literal["6", "7_3_plus_4", "7_4_plus_3", "8", "9", "10"]


class SubjectPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sample_code: str | None = Field(default=None, min_length=1, max_length=60)
    urine_collection_volume_ml: float | None = Field(default=None, ge=0, le=2000)
    clinical_pathway: Pathway | None = None
    optical_zinc_score_0_4: int | None = Field(default=None, ge=0, le=4)
    optical_psa_score_0_4: int | None = Field(default=None, ge=0, le=4)

class ClassificationPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record_purpose: Literal["clinical", "research", "calibration", "unclassified"] | None = None
    study_code: str | None = Field(default=None, max_length=80)
    calibration_code: str | None = Field(default=None, max_length=80)
    calibration_analyte: Literal["uzinc", "upsa"] | None = None
    nominal_concentration_ug_ml: float | None = Field(default=None, ge=0)
    replicate_number: int | None = Field(default=None, ge=1)
    notes: str | None = Field(default=None, max_length=500)

class ClinicalPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    age: int | None = Field(default=None, ge=18, le=120)
    serum_psa_ng_ml: float | None = Field(default=None, ge=0)
    dre_result: Literal["not_suspicious", "suspicious", "indeterminate"] | None = None
    pirads: int | None = Field(default=None, ge=1, le=5)
    prostate_volume_ml: float | None = Field(default=None, gt=0)
    gleason_score: Gleason | None = None
    diagnosis: Diagnosis | None = None


class InstrumentPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value_ug_ml: float | None = Field(default=None, ge=0)
    execution_date: date | None = None
    rapid_test_frozen: bool = False
    rapid_test_frozen_date: date | None = None
    instrumental_frozen: bool = False
    instrumental_frozen_date: date | None = None

    @model_validator(mode="after")
    def validate_frozen_dates(self):
        if self.rapid_test_frozen and self.rapid_test_frozen_date is None:
            raise ValueError("rapid_test_frozen_date is required when rapid_test_frozen is true")
        if not self.rapid_test_frozen:
            self.rapid_test_frozen_date = None
        if self.instrumental_frozen and self.instrumental_frozen_date is None:
            raise ValueError("instrumental_frozen_date is required when instrumental_frozen is true")
        if not self.instrumental_frozen:
            self.instrumental_frozen_date = None
        return self


class RecordPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: SubjectPatch | None = None
    classification: ClassificationPatch | None = None
    clinical: ClinicalPatch | None = None
    upsa: InstrumentPatch | None = None
    uzinc: InstrumentPatch | None = None
    notes: str | None = Field(default=None, max_length=4000)


class RecordCreate(BaseModel):
    model_config = ConfigDict(extra="allow")
    schema_version: str | None = None
    storage_mode: str | None = None
    record: dict[str, Any]
    subject: dict[str, Any]
    acquisition: dict[str, Any] | None = None
    analysis: dict[str, Any]
    archive_crop: dict[str, Any] | None = None
    classification: dict[str, Any] | None = None
    manual_data: dict[str, Any] | None = None


class RecordSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    base_filename: str
    sample_code: str
    captured_at: datetime
    clinical_pathway: str | None
    record_purpose: str
    study_code: str | None
    calibration_code: str | None
    calibration_analyte: str | None
    nominal_concentration_ug_ml: float | None
    replicate_number: int | None
    optical_zinc_score_0_4: int | None
    optical_psa_score_0_4: int | None
    zinc_red_excess: float | None
    psa_area_t_c_ratio: float | None
    diagnosis: str | None
    test_state: str | None
    test_valid: bool
    updated_at: datetime


class RecordDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    base_filename: str
    sample_code: str
    progressive_number: int | None
    captured_at: datetime
    clinical_pathway: str | None
    record_purpose: str
    study_code: str | None
    calibration_code: str | None
    calibration_analyte: str | None
    nominal_concentration_ug_ml: float | None
    replicate_number: int | None
    urine_collection_volume_ml: float | None
    optical_zinc_score_0_4: int | None
    optical_psa_score_0_4: int | None
    zinc_red_excess: float | None
    psa_area_t_c_ratio: float | None
    test_state: str | None
    test_valid: bool
    lot_id: str | None
    age: int | None
    serum_psa_ng_ml: float | None
    dre_result: str | None
    pirads: int | None
    prostate_volume_ml: float | None
    gleason_score: str | None
    diagnosis: str | None
    upsa_instrumental_ug_ml: float | None
    upsa_execution_date: date | None
    upsa_rapid_frozen: bool
    upsa_rapid_frozen_date: date | None
    upsa_instrumental_frozen: bool
    upsa_instrumental_frozen_date: date | None
    uzinc_instrumental_ug_ml: float | None
    uzinc_execution_date: date | None
    uzinc_rapid_frozen: bool
    uzinc_rapid_frozen_date: date | None
    uzinc_instrumental_frozen: bool
    uzinc_instrumental_frozen_date: date | None
    raw_record: dict[str, Any]
    notes: str | None
    created_at: datetime
    updated_at: datetime
