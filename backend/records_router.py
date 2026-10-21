import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import get_db
from record_models import TestRecord
from record_schemas import RecordCreate, RecordDetail, RecordPatch, RecordSummary
from record_service import create_or_update_record, patch_record

router = APIRouter(prefix="/records", tags=["records"])


@router.post("", response_model=RecordDetail, status_code=status.HTTP_201_CREATED)
def create_record(payload: RecordCreate, db: Session = Depends(get_db)):
    return create_or_update_record(db, payload)


@router.get("", response_model=list[RecordSummary])
def list_records(
    sample_code: str | None = None,
    clinical_pathway: str | None = None,
    diagnosis: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = select(TestRecord)
    if sample_code:
        query = query.where(TestRecord.sample_code.ilike(f"%{sample_code}%"))
    if clinical_pathway:
        query = query.where(TestRecord.clinical_pathway == clinical_pathway)
    if diagnosis:
        query = query.where(TestRecord.diagnosis == diagnosis)
    query = query.order_by(TestRecord.captured_at.desc()).offset(offset).limit(limit)
    return list(db.scalars(query))


@router.get("/{record_id}", response_model=RecordDetail)
def get_record(record_id: uuid.UUID, db: Session = Depends(get_db)):
    record = db.get(TestRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@router.patch("/{record_id}", response_model=RecordDetail)
def update_record(record_id: uuid.UUID, payload: RecordPatch, db: Session = Depends(get_db)):
    record = db.get(TestRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return patch_record(db, record, payload)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: uuid.UUID, db: Session = Depends(get_db)):
    record = db.get(TestRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    db.delete(record)
    db.commit()
