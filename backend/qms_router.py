import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from database import get_db
from qms_models import QmsLot, QmsLotRecordType, QmsLotRelationship, QmsProduct
from qms_schemas import LotCreate, LotOut, ProductOut, RelationshipOut
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
