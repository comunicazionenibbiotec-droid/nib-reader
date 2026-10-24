import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator

GROUPS = {"3-4", "2", "1", "0"}
FILTERS = {"none", "pirads", "psa", "dre", "pirads_psa", "pirads_dre", "dre_psa", "pirads_dre_psa"}

class RiskProbabilityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    adjusted_any: float | None = Field(default=None, ge=0, le=100)
    adjusted_ge_3_4: float | None = Field(default=None, ge=0, le=100)
    adjusted_ge_4_3: float | None = Field(default=None, ge=0, le=100)
    @model_validator(mode="after")
    def validate_order(self):
        values = [self.adjusted_any, self.adjusted_ge_3_4, self.adjusted_ge_4_3]
        if all(v is not None for v in values) and not (values[0] >= values[1] >= values[2]):
            raise ValueError("Le probabilita devono rispettare: tumore >= Gleason 3+4 >= Gleason 4+3")
        return self

class RiskProbabilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    matrix_version: str
    zinc_group: str
    upsa_group: str
    clinical_filter: str
    clinical_filter_label: str
    n_subjects: int
    events_any: int
    events_ge_3_4: int
    events_ge_4_3: int
    raw_any: float | None
    raw_ge_3_4: float | None
    raw_ge_4_3: float | None
    adjusted_any: float | None
    adjusted_ge_3_4: float | None
    adjusted_ge_4_3: float | None
    stability_note: str | None
    method: str
    updated_at: datetime
