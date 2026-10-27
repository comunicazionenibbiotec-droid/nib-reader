import statistics
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from database import get_db
from calibration_models import CalibrationSession
from calibration_schemas import CalibrationSessionCreate, CalibrationSessionDetail
from qms_models import QmsLot
from record_models import TestRecord

router = APIRouter(prefix="/calibrations", tags=["calibrations"])


def _records_query(session: CalibrationSession):
    # calibration_code is unique in calibration_sessions and is the stable
    # relation between a session and its acquisitions. Do not also filter by
    # TestRecord.lot_id: depending on the records schema that field can contain
    # the human-readable Lot Record code while the session stores the QMS UUID.
    return select(TestRecord).where(
        TestRecord.record_purpose == "calibration",
        TestRecord.calibration_code == session.calibration_code,
    )


def _detail(db: Session, session: CalibrationSession) -> dict[str, Any]:
    count = db.scalar(select(func.count()).select_from(_records_query(session).subquery())) or 0
    return {
        "id": session.id,
        "calibration_code": session.calibration_code,
        "analyte": session.analyte,
        "lot_id": session.lot_id,
        "lot_code": session.lot.full_lot_record_code,
        "status": session.status,
        "opened_at": session.opened_at,
        "closed_at": session.closed_at,
        "notes": session.notes,
        "acquisition_count": int(count),
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }


def _metric(raw: dict[str, Any], *path: str) -> float | None:
    current: Any = raw
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    try:
        value = float(current)
        return value if value == value else None
    except (TypeError, ValueError):
        return None


def _measurement(record: TestRecord) -> dict[str, float | int] | None:
    raw = record.raw_record or {}
    manual = ((raw.get("analysis") or {}).get("upsa_calibration") or {})
    profile = raw.get("roi_C_analysis") or ((raw.get("roi_review") or {}).get("roi_profile_analysis") or {})
    source = manual if manual else profile
    t = source.get("test_line") or {}
    c = source.get("control_line") or {}
    ratios = source.get("ratios") or {}
    values = {
        "t_height": _metric(t, "height"),
        "t_area": _metric(t, "area"),
        "c_height": _metric(c, "height"),
        "c_area": _metric(c, "area"),
        "height_ratio": _metric(ratios, "height_T_over_C"),
        "area_ratio": _metric(ratios, "area_T_over_C"),
    }
    if values["height_ratio"] is None and values["t_height"] is not None and values["c_height"] not in (None, 0):
        values["height_ratio"] = values["t_height"] / values["c_height"]
    if values["area_ratio"] is None and values["t_area"] is not None and values["c_area"] not in (None, 0):
        values["area_ratio"] = values["t_area"] / values["c_area"]
    score = record.optical_psa_score_0_4
    if score is None or any(values[key] is None for key in values):
        return None
    return {"score": int(score), **values}


def _aggregate(values: list[float]) -> dict[str, float]:
    return {"median": statistics.median(values), "minimum": min(values), "maximum": max(values)}


@router.post("", response_model=CalibrationSessionDetail, status_code=status.HTTP_201_CREATED)
def open_calibration(payload: CalibrationSessionCreate, db: Session = Depends(get_db)):
    code = payload.calibration_code.strip()
    lot = db.get(QmsLot, payload.lot_id)
    if lot is None:
        raise HTTPException(status_code=404, detail="Lotto non trovato")
    if lot.lr_document_code != "LR-000198":
        raise HTTPException(status_code=409, detail="La calibrazione uPSA richiede un lotto LR-000198")
    existing = db.scalar(select(CalibrationSession).where(CalibrationSession.calibration_code == code))
    if existing:
        if existing.lot_id != payload.lot_id:
            raise HTTPException(status_code=409, detail="Il codice calibrazione appartiene a un lotto diverso")
        if existing.status == "closed":
            raise HTTPException(status_code=409, detail="Calibration is already closed")
        return _detail(db, existing)
    session = CalibrationSession(calibration_code=code, analyte=payload.analyte, lot_id=payload.lot_id, notes=payload.notes)
    db.add(session); db.commit(); db.refresh(session)
    return _detail(db, session)


@router.get("/reference")
def calibration_reference(lot_id: uuid.UUID, score: int = Query(ge=0, le=4), db: Session = Depends(get_db)):
    session = db.scalar(select(CalibrationSession).where(
        CalibrationSession.lot_id == lot_id,
        CalibrationSession.analyte == "upsa",
        CalibrationSession.status == "closed",
    ).order_by(CalibrationSession.closed_at.desc()))
    if session is None:
        raise HTTPException(status_code=404, detail="Nessuna calibrazione uPSA chiusa per questo lotto")
    measurements = []
    for record in db.scalars(_records_query(session)):
        item = _measurement(record)
        if item and item["score"] == score:
            measurements.append(item)
    if not measurements:
        raise HTTPException(status_code=404, detail="Nessun riferimento per lo score ottico selezionato")
    metric_names = ["t_height", "t_area", "c_height", "c_area", "height_ratio", "area_ratio"]
    return {
        "calibration_code": session.calibration_code,
        "lot_id": session.lot_id,
        "lot_code": session.lot.full_lot_record_code,
        "closed_at": session.closed_at,
        "score": score,
        "replicate_count": len(measurements),
        "metrics": {name: _aggregate([float(row[name]) for row in measurements]) for name in metric_names},
    }


@router.get("/{calibration_code}", response_model=CalibrationSessionDetail)
def get_calibration(calibration_code: str, db: Session = Depends(get_db)):
    session = db.scalar(select(CalibrationSession).where(CalibrationSession.calibration_code == calibration_code))
    if not session: raise HTTPException(status_code=404, detail="Calibration not found")
    return _detail(db, session)


@router.post("/{calibration_code}/close", response_model=CalibrationSessionDetail)
def close_calibration(calibration_code: str, db: Session = Depends(get_db)):
    session = db.scalar(select(CalibrationSession).where(CalibrationSession.calibration_code == calibration_code))
    if not session: raise HTTPException(status_code=404, detail="Calibration not found")
    count = db.scalar(select(func.count()).select_from(_records_query(session).subquery())) or 0
    if count < 1:
        raise HTTPException(status_code=409, detail="Salva almeno una replica della tabella prima di chiudere la calibrazione")
    session.status = "closed"; session.closed_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(session)
    return _detail(db, session)
