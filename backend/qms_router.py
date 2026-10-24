import json
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from database import get_db
from qms_models import QmsLot, QmsLotRecordType, QmsLotRelationship, QmsProduct, QmsQcRecord
from qms_schemas import LotCreate, LotOut, ProductOut, RelationshipOut, QcRecordCreate
from qms_service import build_full_code, create_lot, next_progressive

router = APIRouter(prefix="/qms", tags=["qms"])

@router.get("/products", response_model=list[ProductOut])
def products(db: Session = Depends(get_db)):
    return list(db.scalars(select(QmsProduct).where(QmsProduct.active.is_(True)).order_by(QmsProduct.pm_code)))

@router.get("/lot-record-types")
def lot_record_types(db: Session = Depends(get_db)):
    rows = db.execute(select(QmsLotRecordType, QmsProduct).join(QmsProduct).where(QmsLotRecordType.active.is_(True)).order_by(QmsLotRecordType.lr_document_code)).all()
    result=[]
    for record_type, product in rows:
        nxt=next_progressive(db, record_type.id)
        result.append({"id":record_type.id,"product_id":product.id,"pm_code":product.pm_code,"product_name":product.product_name,"lr_document_code":record_type.lr_document_code,"operation_code":record_type.operation_code,"operation_name":record_type.operation_name,"stage":record_type.stage,"progressive_digits":record_type.progressive_digits,"next_progressive":nxt,"next_full_lot_record_code":build_full_code(record_type,nxt)})
    return result

@router.get("/lots", response_model=list[LotOut])
def lots(pm_code: str | None=None, lr_document_code: str | None=None, status_value: str | None=Query(default=None, alias="status"), limit: int=Query(default=200, ge=1, le=500), db: Session=Depends(get_db)):
    query=select(QmsLot)
    if pm_code: query=query.where(QmsLot.pm_code==pm_code)
    if lr_document_code: query=query.where(QmsLot.lr_document_code==lr_document_code)
    if status_value: query=query.where(QmsLot.status==status_value)
    return list(db.scalars(query.order_by(QmsLot.created_at.desc()).limit(limit)))

@router.post("/lots", response_model=LotOut, status_code=status.HTTP_201_CREATED)
def add_lot(payload: LotCreate, db: Session=Depends(get_db)):
    try: return create_lot(db,payload)
    except ValueError as error: raise HTTPException(status_code=409, detail=str(error))

@router.get("/lots/{lot_id}", response_model=LotOut)
def get_lot(lot_id: uuid.UUID, db: Session=Depends(get_db)):
    lot=db.get(QmsLot,lot_id)
    if lot is None: raise HTTPException(status_code=404,detail="Lotto non trovato")
    return lot

@router.get("/lots/{lot_id}/relationships", response_model=list[RelationshipOut])
def relationships(lot_id: uuid.UUID, db: Session=Depends(get_db)):
    return list(db.scalars(select(QmsLotRelationship).where((QmsLotRelationship.parent_lot_id==lot_id)|(QmsLotRelationship.child_lot_id==lot_id))))


def serialize_qc_record(record: QmsQcRecord, lot: QmsLot):
    return {"id":record.id,"lot_id":record.lot_id,"lot_code":lot.full_lot_record_code,"qc_type":record.qc_type,"capture_mode":record.capture_mode,"captured_at":record.captured_at,"image_width":record.image_width,"image_height":record.image_height,"image_filename":record.image_filename,"roi_data":json.loads(record.roi_data_json),"analysis_data":json.loads(record.analysis_data_json) if record.analysis_data_json else None,"created_at":record.created_at}

@router.post("/qc-records", status_code=status.HTTP_201_CREATED)
def add_qc_record(payload: QcRecordCreate, db: Session = Depends(get_db)):
    lot=db.get(QmsLot,payload.lot_id)
    if lot is None: raise HTTPException(status_code=404,detail="Lotto non trovato")
    if payload.qc_type=="colorimetric_pad" and lot.lr_document_code!="LR-000104": raise HTTPException(status_code=409,detail="Il QC del pad richiede un lotto LR-000104")
    record=QmsQcRecord(lot_id=lot.id,qc_type=payload.qc_type,capture_mode=payload.capture_mode,captured_at=payload.captured_at,image_width=payload.image_width,image_height=payload.image_height,image_filename=payload.image_filename,roi_data_json=json.dumps(payload.roi_data,ensure_ascii=False),analysis_data_json=json.dumps(payload.analysis_data,ensure_ascii=False) if payload.analysis_data else None)
    db.add(record);db.commit();db.refresh(record);return serialize_qc_record(record,lot)

@router.get("/qc-records")
def qc_records(lot_id: uuid.UUID | None=None,qc_type: str | None=None,limit:int=Query(default=200,ge=1,le=500),db:Session=Depends(get_db)):
    query=select(QmsQcRecord,QmsLot).join(QmsLot)
    if lot_id: query=query.where(QmsQcRecord.lot_id==lot_id)
    if qc_type: query=query.where(QmsQcRecord.qc_type==qc_type)
    rows=db.execute(query.order_by(QmsQcRecord.captured_at.desc()).limit(limit)).all()
    return [serialize_qc_record(record,lot) for record,lot in rows]
