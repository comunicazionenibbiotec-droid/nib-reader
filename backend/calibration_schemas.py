import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class CalibrationSessionCreate(BaseModel):
    calibration_code: str = Field(min_length=1, max_length=80)
    analyte: Literal["upsa", "uzinc"] = "upsa"
    lot_id: uuid.UUID
    notes: str | None = Field(default=None, max_length=1000)

class CalibrationLotUpdate(BaseModel):
    lot_id: uuid.UUID

class CalibrationSessionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    calibration_code: str
    analyte: str
    lot_id: uuid.UUID | None
    lot_code: str | None
    status: str
    opened_at: datetime
    closed_at: datetime | None
    notes: str | None
    acquisition_count: int = 0
    created_at: datetime
    updated_at: datetime
