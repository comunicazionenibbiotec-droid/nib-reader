import uuid
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator

LOT_STATUSES = {"draft", "active", "released", "rejected", "closed", "invalidated"}
RELATIONSHIP_TYPES = {"processed_into", "cut_into", "assembled_into", "used_in", "packed_into", "reference_material_for"}

class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    pm_code: str
    product_name: str
    product_category: str
    product_stage: str
    active: bool

class LotRecordTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    product_id: uuid.UUID
    pm_code: str
    product_name: str
    lr_document_code: str
    operation_code: str
    operation_name: str
    stage: str
    progressive_digits: int
    next_progressive: int
    next_full_lot_record_code: str

class LotCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lot_record_type_id: uuid.UUID
    manufacturing_date: date | None = None
    expiry_date: date | None = None
    protocol_version: str | None = Field(default=None, max_length=80)
    operator: str | None = Field(default=None, max_length=120)
    status: str = "draft"
    notes: str | None = Field(default=None, max_length=4000)
    parent_lot_ids: list[uuid.UUID] = []
    relationship_type: str | None = None
    @model_validator(mode="after")
    def validate_qms(self):
        if self.status not in LOT_STATUSES:
            raise ValueError("Stato lotto non valido")
        if self.parent_lot_ids and self.relationship_type not in RELATIONSHIP_TYPES:
            raise ValueError("Selezionare un tipo di relazione QMS valido")
        return self

class LotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    lot_record_type_id: uuid.UUID
    pm_code: str
    lr_document_code: str
    lot_progressive: int
    full_lot_record_code: str
    manufacturing_date: date | None
    expiry_date: date | None
    protocol_version: str | None
    operator: str | None
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime

class RelationshipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    parent_lot_id: uuid.UUID
    child_lot_id: uuid.UUID
    relationship_type: str
    notes: str | None


class QcRecordCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lot_id: uuid.UUID
    qc_type: str
    capture_mode: str
    captured_at: datetime
    image_width: int
    image_height: int
    image_filename: str | None = None
    roi_data: dict
    analysis_data: dict | None = None
