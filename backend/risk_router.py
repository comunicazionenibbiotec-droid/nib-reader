import json
from pathlib import Path
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from database import get_db
from risk_models import RiskProbabilityRow
from risk_schemas import RiskProbabilityOut, RiskProbabilityUpdate

router = APIRouter(prefix="/risk", tags=["risk"])
DEFAULT_VERSION = "2026-10-24-jeffreys-v1"

def seed_path():
    return Path(__file__).with_name("risk_matrix_seed.json")

def seed_risk_probability_matrix(db: Session):
    existing = db.scalar(select(RiskProbabilityRow.id).where(RiskProbabilityRow.matrix_version == DEFAULT_VERSION).limit(1))
    if existing is not None:
        return
    payload = json.loads(seed_path().read_text(encoding="utf-8"))
    for item in payload["rows"]:
        probability = item["probabilities"]
        raw = item["raw_percent"]
        events = item["events"]
        db.add(RiskProbabilityRow(
            matrix_version=payload["version"], zinc_group=item["zinc_group"], upsa_group=item["upsa_group"],
            clinical_filter=item["clinical_filter"], clinical_filter_label=item["clinical_filter_label"],
            n_subjects=item["n"], events_any=events["any"], events_ge_3_4=events["ge_3_4"], events_ge_4_3=events["ge_4_3"],
            raw_any=raw["any"], raw_ge_3_4=raw["ge_3_4"], raw_ge_4_3=raw["ge_4_3"],
            adjusted_any=probability["any"], adjusted_ge_3_4=probability["ge_3_4"], adjusted_ge_4_3=probability["ge_4_3"],
            stability_note=item["note"] or None, method=payload["method"]
        ))
    db.commit()

@router.get("/probability-matrix", response_model=list[RiskProbabilityOut])
def probability_matrix(db: Session = Depends(get_db)):
    return list(db.scalars(select(RiskProbabilityRow).where(RiskProbabilityRow.matrix_version == DEFAULT_VERSION).order_by(RiskProbabilityRow.zinc_group.desc(), RiskProbabilityRow.upsa_group.desc(), RiskProbabilityRow.clinical_filter)))

@router.put("/probability-matrix/{row_id}", response_model=RiskProbabilityOut)
def update_probability(row_id: uuid.UUID, payload: RiskProbabilityUpdate, db: Session = Depends(get_db)):
    row = db.get(RiskProbabilityRow, row_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Riga probabilita non trovata")
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    db.commit(); db.refresh(row)
    return row

@router.post("/probability-matrix/reset", response_model=list[RiskProbabilityOut])
def reset_probability_matrix(db: Session = Depends(get_db)):
    payload = json.loads(seed_path().read_text(encoding="utf-8"))
    indexed = {(r.zinc_group, r.upsa_group, r.clinical_filter): r for r in db.scalars(select(RiskProbabilityRow).where(RiskProbabilityRow.matrix_version == DEFAULT_VERSION))}
    for item in payload["rows"]:
        row = indexed.get((item["zinc_group"], item["upsa_group"], item["clinical_filter"]))
        if row:
            row.adjusted_any = item["probabilities"]["any"]
            row.adjusted_ge_3_4 = item["probabilities"]["ge_3_4"]
            row.adjusted_ge_4_3 = item["probabilities"]["ge_4_3"]
    db.commit()
    return probability_matrix(db)
