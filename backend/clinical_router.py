import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from database import get_db
from clinical_models import ClinicalPatient, ClinicalCase, ClinicalVisit, MriOutcome, BiopsyOutcome, ProgressionOutcome, ModelPrediction
from clinical_schemas import *
from clinical_service import add_visit, upsert_mri, upsert_biopsy, upsert_progression
router = APIRouter(prefix="/clinical", tags=["clinical-longitudinal"])

def require(db, model, item_id, label):
    item=db.get(model,item_id)
    if item is None: raise HTTPException(404,f"{label} not found")
    return item

@router.post("/patients", response_model=PatientOut, status_code=201)
def create_patient(payload: PatientCreate, db: Session=Depends(get_db)):
    existing=db.scalar(select(ClinicalPatient).where(ClinicalPatient.patient_code==payload.patient_code))
    if existing: return existing
    row=ClinicalPatient(**payload.model_dump()); db.add(row); db.commit(); db.refresh(row); return row

@router.get("/patients", response_model=list[PatientOut])
def list_patients(patient_code: str|None=None, db: Session=Depends(get_db)):
    q=select(ClinicalPatient)
    if patient_code: q=q.where(ClinicalPatient.patient_code.ilike(f"%{patient_code}%"))
    return list(db.scalars(q.order_by(ClinicalPatient.created_at.desc()).limit(500)))

@router.post("/cases", response_model=CaseOut, status_code=201)
def create_case(payload: CaseCreate, db: Session=Depends(get_db)):
    require(db,ClinicalPatient,payload.patient_id,"Patient")
    row=ClinicalCase(**payload.model_dump()); db.add(row); db.commit(); db.refresh(row); return row

@router.get("/cases", response_model=list[CaseOut])
def list_cases(patient_id: uuid.UUID|None=None, pathway: str|None=None, db: Session=Depends(get_db)):
    q=select(ClinicalCase)
    if patient_id: q=q.where(ClinicalCase.patient_id==patient_id)
    if pathway: q=q.where(ClinicalCase.clinical_pathway==pathway)
    return list(db.scalars(q.order_by(ClinicalCase.created_at.desc()).limit(500)))

@router.post("/cases/{case_id}/visits", response_model=VisitOut, status_code=201)
def create_visit(case_id: uuid.UUID, payload: VisitCreate, db: Session=Depends(get_db)):
    return add_visit(db,require(db,ClinicalCase,case_id,"Case"),payload)

@router.get("/cases/{case_id}/visits", response_model=list[VisitOut])
def list_visits(case_id: uuid.UUID, db: Session=Depends(get_db)):
    require(db,ClinicalCase,case_id,"Case")
    return list(db.scalars(select(ClinicalVisit).where(ClinicalVisit.case_id==case_id).order_by(ClinicalVisit.visit_date)))

@router.put("/visits/{visit_id}/mri", response_model=MriOut)
def save_mri(visit_id: uuid.UUID, payload: MriUpsert, db: Session=Depends(get_db)):
    return upsert_mri(db,require(db,ClinicalVisit,visit_id,"Visit"),payload)

@router.put("/visits/{visit_id}/biopsy", response_model=BiopsyOut)
def save_biopsy(visit_id: uuid.UUID, payload: BiopsyUpsert, db: Session=Depends(get_db)):
    return upsert_biopsy(db,require(db,ClinicalVisit,visit_id,"Visit"),payload)

@router.put("/cases/{case_id}/progression", response_model=ProgressionOut)
def save_progression(case_id: uuid.UUID, payload: ProgressionUpsert, db: Session=Depends(get_db)):
    case=require(db,ClinicalCase,case_id,"Case")
    if case.clinical_pathway!="active_surveillance": raise HTTPException(409,"Progression is only available for active surveillance cases")
    return upsert_progression(db,case,payload)

@router.post("/cases/{case_id}/predictions", response_model=PredictionOut, status_code=201)
def freeze_prediction(case_id: uuid.UUID, payload: PredictionCreate, db: Session=Depends(get_db)):
    case=require(db,ClinicalCase,case_id,"Case")
    if payload.visit_id:
        visit=require(db,ClinicalVisit,payload.visit_id,"Visit")
        if visit.case_id!=case.id: raise HTTPException(409,"Visit does not belong to case")
    row=ModelPrediction(case_id=case.id, immutable=True, **payload.model_dump())
    db.add(row); db.commit(); db.refresh(row); return row

@router.get("/cases/{case_id}/predictions", response_model=list[PredictionOut])
def list_predictions(case_id: uuid.UUID, db: Session=Depends(get_db)):
    require(db,ClinicalCase,case_id,"Case")
    return list(db.scalars(select(ModelPrediction).where(ModelPrediction.case_id==case_id).order_by(ModelPrediction.predicted_at)))

@router.get("/cases/{case_id}")
def case_detail(case_id: uuid.UUID, db: Session=Depends(get_db)):
    case=require(db,ClinicalCase,case_id,"Case")
    visits=list(db.scalars(select(ClinicalVisit).where(ClinicalVisit.case_id==case_id).order_by(ClinicalVisit.visit_date)))
    return {"case":CaseOut.model_validate(case),"visits":[{"visit":VisitOut.model_validate(v),"mri":MriOut.model_validate(x) if (x:=db.get(MriOutcome,v.id)) else None,"biopsy":BiopsyOut.model_validate(b) if (b:=db.get(BiopsyOutcome,v.id)) else None} for v in visits],"progression":ProgressionOut.model_validate(p) if (p:=db.get(ProgressionOutcome,case.id)) else None}
