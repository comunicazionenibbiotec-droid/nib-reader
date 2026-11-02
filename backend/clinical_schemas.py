import uuid
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Pathway = Literal["pre_mri", "pre_biopsy", "active_surveillance"]

class PatientCreate(BaseModel):
    patient_code: str = Field(min_length=1, max_length=80)
    birth_date: date | None = None
    notes: str | None = Field(default=None, max_length=4000)

class CaseCreate(BaseModel):
    patient_id: uuid.UUID
    clinical_pathway: Pathway
    recruitment_center: str | None = Field(default=None, max_length=120)
    diagnosis_date: date | None = None
    initial_diagnosis: str | None = Field(default=None, max_length=60)
    initial_gleason_primary: int | None = Field(default=None, ge=3, le=5)
    initial_gleason_secondary: int | None = Field(default=None, ge=3, le=5)
    initial_isup_grade_group: int | None = Field(default=None, ge=1, le=5)
    initial_stage: str | None = Field(default=None, max_length=40)
    @model_validator(mode="after")
    def active_surveillance_requires_diagnosis(self):
        if self.clinical_pathway == "active_surveillance" and self.diagnosis_date is None:
            raise ValueError("diagnosis_date is required for active surveillance")
        return self

class VisitCreate(BaseModel):
    record_id: uuid.UUID | None = None
    visit_code: str = Field(min_length=1, max_length=40)
    visit_date: date
    serum_psa_ng_ml: float | None = Field(default=None, ge=0)
    prostate_volume_ml: float | None = Field(default=None, gt=0)
    dre_result: str | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=4000)

class MriUpsert(BaseModel):
    status: Literal["NOT_SCHEDULED", "SCHEDULED", "COMPLETED", "NOT_PERFORMED", "UNKNOWN"] = "UNKNOWN"
    mri_date: date | None = None
    pirads_score: int | None = Field(default=None, ge=1, le=5)
    suspicious_lesion: bool | None = None
    lesion_count: int | None = Field(default=None, ge=0)
    index_lesion_size_mm: float | None = Field(default=None, ge=0)
    index_lesion_location: str | None = Field(default=None, max_length=160)
    prostate_volume_ml: float | None = Field(default=None, gt=0)
    possible_benign_mimic: bool = False
    benign_mimic_type: Literal["calcifications", "prostatitis_inflammation", "bph_benign_nodule", "hemorrhage", "fibrosis", "other"] | None = None
    benign_mimic_notes: str | None = Field(default=None, max_length=4000)
    report_verified: bool = False
    report_source: str | None = Field(default=None, max_length=40)
    @model_validator(mode="after")
    def validate_completed(self):
        if self.status == "COMPLETED" and (self.mri_date is None or self.pirads_score is None):
            raise ValueError("Completed MRI requires mri_date and pirads_score")
        if not self.possible_benign_mimic:
            self.benign_mimic_type = None; self.benign_mimic_notes = None
        return self

class BiopsyUpsert(BaseModel):
    status: Literal["NOT_INDICATED", "INDICATED", "SCHEDULED", "COMPLETED", "DEFERRED", "DECLINED", "UNKNOWN"] = "UNKNOWN"
    biopsy_date: date | None = None
    non_performance_reason: str | None = Field(default=None, max_length=200)
    result: Literal["negative", "benign", "prostatitis", "BPH", "HGPIN", "ASAP", "carcinoma", "other"] | None = None
    gleason_primary: int | None = Field(default=None, ge=3, le=5)
    gleason_secondary: int | None = Field(default=None, ge=3, le=5)
    isup_grade_group: int | None = Field(default=None, ge=1, le=5)
    positive_cores: int | None = Field(default=None, ge=0)
    total_cores: int | None = Field(default=None, ge=1)
    max_core_involvement_percent: float | None = Field(default=None, ge=0, le=100)
    report_verified: bool = False
    @model_validator(mode="after")
    def validate_biopsy(self):
        if self.status == "COMPLETED" and (self.biopsy_date is None or self.result is None):
            raise ValueError("Completed biopsy requires biopsy_date and result")
        if self.positive_cores is not None and self.total_cores is not None and self.positive_cores > self.total_cores:
            raise ValueError("positive_cores cannot exceed total_cores")
        return self

class ProgressionUpsert(BaseModel):
    progression_status: Literal["YES", "NO", "NOT_EVALUABLE"] = "NOT_EVALUABLE"
    progression_date: date | None = None
    last_followup_date: date | None = None
    progression_type: list[Literal["isup_upgrading", "gleason_increase", "tumor_volume_increase", "positive_cores_increase", "mri_progression", "clinical_progression", "other"]] = []
    followup_gleason_primary: int | None = Field(default=None, ge=3, le=5)
    followup_gleason_secondary: int | None = Field(default=None, ge=3, le=5)
    followup_isup_grade_group: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = Field(default=None, max_length=4000)
    @model_validator(mode="after")
    def validate_progression(self):
        if self.progression_status == "YES" and self.progression_date is None:
            raise ValueError("progression_date is required when progression is YES")
        if self.progression_status != "YES": self.progression_date = None
        return self

class PredictionCreate(BaseModel):
    visit_id: uuid.UUID | None = None
    prediction_context: Literal["PRE_MRI", "PRE_BIOPSY", "ACTIVE_SURVEILLANCE"]
    model_version: str = Field(min_length=1, max_length=80)
    probabilities: dict[str, float]
    input_snapshot: dict
    quality_flags: dict = {}
    @model_validator(mode="after")
    def validate_probabilities(self):
        for key, value in self.probabilities.items():
            if not 0 <= float(value) <= 100: raise ValueError(f"Probability {key} must be between 0 and 100")
        return self

class OrmOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
class PatientOut(OrmOut):
    id: uuid.UUID; patient_code: str; birth_date: date | None; notes: str | None; created_at: datetime; updated_at: datetime
class CaseOut(OrmOut):
    id: uuid.UUID; patient_id: uuid.UUID; clinical_pathway: str; recruitment_center: str | None; diagnosis_date: date | None; initial_diagnosis: str | None; initial_gleason_primary: int | None; initial_gleason_secondary: int | None; initial_isup_grade_group: int | None; initial_stage: str | None; status: str; created_at: datetime; updated_at: datetime
class VisitOut(OrmOut):
    id: uuid.UUID; case_id: uuid.UUID; record_id: uuid.UUID | None; visit_code: str; visit_date: date; timepoint_months: float | None; serum_psa_ng_ml: float | None; prostate_volume_ml: float | None; psa_density: float | None; dre_result: str | None; notes: str | None; created_at: datetime
class MriOut(OrmOut):
    visit_id: uuid.UUID; status: str; mri_date: date | None; pirads_score: int | None; suspicious_lesion: bool | None; lesion_count: int | None; index_lesion_size_mm: float | None; index_lesion_location: str | None; prostate_volume_ml: float | None; possible_benign_mimic: bool; benign_mimic_type: str | None; benign_mimic_notes: str | None; report_verified: bool; report_source: str | None
class BiopsyOut(OrmOut):
    visit_id: uuid.UUID; status: str; biopsy_date: date | None; non_performance_reason: str | None; result: str | None; gleason_primary: int | None; gleason_secondary: int | None; gleason_total: int | None; isup_grade_group: int | None; positive_cores: int | None; total_cores: int | None; max_core_involvement_percent: float | None; any_pca: bool | None; clinically_significant_pca: bool | None; gleason_ge_7: bool | None; gleason_gt_7: bool | None; report_verified: bool
class ProgressionOut(OrmOut):
    case_id: uuid.UUID; progression_status: str; progression_date: date | None; last_followup_date: date | None; months_diagnosis_to_progression: float | None; progression_type: dict; followup_gleason_primary: int | None; followup_gleason_secondary: int | None; followup_isup_grade_group: int | None; notes: str | None
class PredictionOut(OrmOut):
    id: uuid.UUID; case_id: uuid.UUID; visit_id: uuid.UUID | None; prediction_context: str; model_version: str; predicted_at: datetime; probabilities: dict; input_snapshot: dict; quality_flags: dict; immutable: bool
