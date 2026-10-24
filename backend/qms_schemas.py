import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


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
    """Minimal payload used to register a new production lot."""

    model_config = ConfigDict(extra="forbid")

    lot_record_type_id: uuid.UUID
    manufacturing_date: date


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
