import uuid
from typing import Literal
from pydantic import BaseModel, Field, model_validator

class PlanCreate(BaseModel):
    calibration_code: str = Field(min_length=1, max_length=80)
    lot_id: uuid.UUID
    expected_concentrations: int = Field(ge=1, le=10)
    default_replicates: int = Field(ge=1, le=10)

class PointCreate(BaseModel):
    calibration_code: str = Field(min_length=1, max_length=80)
    lot_id: uuid.UUID
    optical_score: int = Field(ge=0, le=4)
    concentration_slot: Literal['A','B']
    instrumental_concentration: float = Field(ge=0)
    concentration_unit: Literal['ug/mL','ng/mL'] = 'ug/mL'
    planned_replicates: int = Field(ge=1, le=10)
    acquisition_mode: Literal['READER','MANUAL'] = 'READER'

class UzincMetricFields(BaseModel):
    lab_l: float | None = None
    lab_a: float | None = None
    lab_b: float | None = None
    hue_lab: float | None = None
    chroma: float | None = None
    a_over_b: float | None = None
    saturation: float | None = None
    r_over_g: float | None = None
    b_over_g: float | None = None
    magenta_index: float | None = None
    delta_e_white: float | None = None
    luminance_ratio: float | None = None
    white_luminance_cv: float | None = Field(default=None, ge=0)
    white_overexposed_fraction: float | None = Field(default=None, ge=0, le=1)
    sample_clipped_fraction: float | None = Field(default=None, ge=0, le=1)
    white_clipped_fraction: float | None = Field(default=None, ge=0, le=1)
    sample_pixel_count: int | None = Field(default=None, ge=0)
    white_pixel_count: int | None = Field(default=None, ge=0)
    disc_detected: bool | None = None
    detection_method: str | None = Field(default=None, max_length=80)
    uzinc_qc_status: Literal['valid','warning','invalid','not_evaluated'] | None = None

    @model_validator(mode='after')
    def derive_a_over_b(self):
        if self.a_over_b is None and self.lab_a is not None and self.lab_b not in (None, 0):
            self.a_over_b = self.lab_a / self.lab_b
        return self

class MeasurementCreate(UzincMetricFields):
    record_id: uuid.UUID | None = None
    replicate_number: int = Field(ge=1, le=10)
    source: Literal['READER','MANUAL','READER_LEGACY'] = 'READER'
    t_height: float | None = None
    t_area: float | None = None
    t_width: float | None = None
    t_fwhm: float | None = None
    c_height: float | None = None
    c_area: float | None = None
    c_width: float | None = None
    c_fwhm: float | None = None
    height_ratio: float | None = None
    area_ratio: float | None = None
    raw_measurement: dict = Field(default_factory=dict)

class UzincMeasurementUpdate(UzincMetricFields):
    raw_measurement: dict | None = None

class SkipCreate(BaseModel):
    reason: str = Field(default='operator_skipped', max_length=200)
