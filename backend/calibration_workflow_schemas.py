import uuid
from typing import Literal
from pydantic import BaseModel,Field
class PlanCreate(BaseModel):
    calibration_code:str=Field(min_length=1,max_length=80)
    lot_id:uuid.UUID
    expected_concentrations:int=Field(ge=1,le=50)
    default_replicates:int=Field(ge=1,le=10)
class PointCreate(BaseModel):
    calibration_code:str=Field(min_length=1,max_length=80)
    lot_id:uuid.UUID
    optical_score:int=Field(ge=0,le=4)
    concentration_slot:Literal['A','B']
    instrumental_concentration:float=Field(ge=0)
    concentration_unit:Literal['ug/mL','ng/mL']='ug/mL'
    planned_replicates:int=Field(ge=1,le=10)
    acquisition_mode:Literal['READER','MANUAL']='READER'
class MeasurementCreate(BaseModel):
    record_id:uuid.UUID|None=None
    replicate_number:int=Field(ge=1,le=10)
    source:Literal['READER','MANUAL']='READER'
    t_height:float|None=None;t_area:float|None=None;t_width:float|None=None;t_fwhm:float|None=None
    c_height:float|None=None;c_area:float|None=None;c_width:float|None=None;c_fwhm:float|None=None
    height_ratio:float|None=None;area_ratio:float|None=None
    raw_measurement:dict=Field(default_factory=dict)
class SkipCreate(BaseModel):
    reason:str=Field(default='operator_skipped',max_length=200)
