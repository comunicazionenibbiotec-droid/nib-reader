from datetime import date
from fastapi import HTTPException
from sqlalchemy.orm import Session
from clinical_models import ClinicalCase, ClinicalVisit, MriOutcome, BiopsyOutcome, ProgressionOutcome

def months_between(start: date | None, end: date | None) -> float | None:
    if not start or not end: return None
    if end < start: raise HTTPException(422, "Outcome date cannot precede diagnosis date")
    return round((end - start).days / 30.4375, 2)

def add_visit(db: Session, case: ClinicalCase, payload):
    if payload.record_id is not None:
        from record_models import TestRecord
        if db.get(TestRecord, payload.record_id) is None: raise HTTPException(404, "Reader record not found")
    visit = ClinicalVisit(case_id=case.id, **payload.model_dump())
    visit.timepoint_months = months_between(case.diagnosis_date, payload.visit_date)
    if payload.serum_psa_ng_ml is not None and payload.prostate_volume_ml:
        visit.psa_density = round(payload.serum_psa_ng_ml / payload.prostate_volume_ml, 6)
    db.add(visit); db.commit(); db.refresh(visit); return visit

def upsert_mri(db: Session, visit: ClinicalVisit, payload):
    row = db.get(MriOutcome, visit.id) or MriOutcome(visit_id=visit.id)
    for k,v in payload.model_dump().items(): setattr(row,k,v)
    db.add(row); db.commit(); db.refresh(row); return row

def upsert_biopsy(db: Session, visit: ClinicalVisit, payload):
    row = db.get(BiopsyOutcome, visit.id) or BiopsyOutcome(visit_id=visit.id)
    data = payload.model_dump()
    for k,v in data.items(): setattr(row,k,v)
    if data.get("gleason_primary") and data.get("gleason_secondary"):
        row.gleason_total = data["gleason_primary"] + data["gleason_secondary"]
    row.any_pca = None if data.get("result") is None else data["result"] == "carcinoma"
    row.clinically_significant_pca = None if row.any_pca is not True else bool((data.get("isup_grade_group") or 0) >= 2)
    row.gleason_ge_7 = None if row.gleason_total is None else row.gleason_total >= 7
    row.gleason_gt_7 = None if row.gleason_total is None else row.gleason_total > 7
    db.add(row); db.commit(); db.refresh(row); return row

def upsert_progression(db: Session, case: ClinicalCase, payload):
    row = db.get(ProgressionOutcome, case.id) or ProgressionOutcome(case_id=case.id)
    data = payload.model_dump()
    for k,v in data.items(): setattr(row,k, {item: True for item in v} if k == "progression_type" else v)
    row.months_diagnosis_to_progression = months_between(case.diagnosis_date, row.progression_date) if row.progression_status == "YES" else None
    if row.last_followup_date and case.diagnosis_date and row.last_followup_date < case.diagnosis_date:
        raise HTTPException(422, "last_followup_date cannot precede diagnosis_date")
    db.add(row); db.commit(); db.refresh(row); return row
