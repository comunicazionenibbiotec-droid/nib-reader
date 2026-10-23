import uuid
from datetime import date, datetime, timezone
from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

def utc_now():
    return datetime.now(timezone.utc)

class QmsProduct(Base):
    __tablename__ = "qms_products"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pm_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    product_name: Mapped[str] = mapped_column(String(160))
    product_category: Mapped[str] = mapped_column(String(50))
    product_stage: Mapped[str] = mapped_column(String(80))
    active: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class QmsLotRecordType(Base):
    __tablename__ = "qms_lot_record_types"
    __table_args__ = (UniqueConstraint("lr_document_code", name="uq_qms_lr_document_code"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("qms_products.id", ondelete="RESTRICT"), index=True)
    lr_document_code: Mapped[str] = mapped_column(String(40), index=True)
    operation_code: Mapped[str] = mapped_column(String(60))
    operation_name: Mapped[str] = mapped_column(String(160))
    stage: Mapped[str] = mapped_column(String(100))
    progressive_digits: Mapped[int] = mapped_column(Integer, default=3)
    active: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[str | None] = mapped_column(Text)
    product: Mapped[QmsProduct] = relationship()

class QmsLot(Base):
    __tablename__ = "qms_lots"
    __table_args__ = (
        UniqueConstraint("lot_record_type_id", "lot_progressive", name="uq_qms_lot_series_progressive"),
        UniqueConstraint("full_lot_record_code", name="uq_qms_full_lot_record_code"),
        Index("ix_qms_lots_status_date", "status", "manufacturing_date"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_record_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("qms_lot_record_types.id", ondelete="RESTRICT"), index=True)
    pm_code: Mapped[str] = mapped_column(String(40), index=True)
    lr_document_code: Mapped[str] = mapped_column(String(40), index=True)
    lot_progressive: Mapped[int] = mapped_column(Integer)
    full_lot_record_code: Mapped[str] = mapped_column(String(60), index=True)
    manufacturing_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    protocol_version: Mapped[str | None] = mapped_column(String(80))
    operator: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    lot_record_type: Mapped[QmsLotRecordType] = relationship()

class QmsLotRelationship(Base):
    __tablename__ = "qms_lot_relationships"
    __table_args__ = (UniqueConstraint("parent_lot_id", "child_lot_id", "relationship_type", name="uq_qms_lot_relationship"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_lot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("qms_lots.id", ondelete="RESTRICT"), index=True)
    child_lot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("qms_lots.id", ondelete="RESTRICT"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
