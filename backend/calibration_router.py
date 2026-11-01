import statistics
import uuid
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from database import get_db
from calibration_models import CalibrationSession
from calibration_workflow_models import CalibrationPoint, CalibrationMeasurement
from calibration_schemas import CalibrationLotUpdate, CalibrationSessionCreate, CalibrationSessionDetail
from qms_models import QmsLot
from record_models import TestRecord

router = APIRouter(prefix="/calibrations", tags=["calibrations"])


def _records_query(session: CalibrationSession):
    # calibration_code is the stable link between the calibration session
    # and its acquisitions. Do not dereference session.lot here because
    # historical sessions may point to a QMS lot that is no longer available.
    return select(TestRecord).where(
        TestRecord.record_purpose == "calibration",
        TestRecord.calibration_code == session.calibration_code,
    )


def _workflow_measurement_count(db: Session, session: CalibrationSession) -> int:
    return int(db.scalar(
        select(func.count()).select_from(CalibrationMeasurement)
        .join(CalibrationPoint, CalibrationMeasurement.point_id == CalibrationPoint.id)
        .where(
            CalibrationPoint.session_id == session.id,
            CalibrationMeasurement.status == "COMPLETED",
        )
    ) or 0)

def _detail(db: Session, session: CalibrationSession) -> dict[str, Any]:
    reader_count = db.scalar(select(func.count()).select_from(_records_query(session).subquery())) or 0
    workflow_count = _workflow_measurement_count(db, session)
    count = max(int(reader_count), workflow_count)
    lot = db.get(QmsLot, session.lot_id) if session.lot_id is not None else None
    return {
        "id": session.id,
        "calibration_code": session.calibration_code,
        "analyte": session.analyte,
        "lot_id": session.lot_id,
        "lot_code": lot.full_lot_record_code if lot is not None else None,
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
    expected_lr = {"upsa": "LR-000122", "uzinc": "LR-000104"}[payload.analyte]
    if lot.lr_document_code != expected_lr:
        raise HTTPException(status_code=409, detail=f"La calibrazione {payload.analyte} richiede un lotto {expected_lr}")
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
    selected_lot = db.get(QmsLot, lot_id)
    if selected_lot is None:
        raise HTTPException(status_code=404, detail="Lotto selezionato non trovato")

    # The Reader may pass either the LF-strip lot itself or the ZenPSA device lot.
    # First try the exact lot; if it is not LR-000122, resolve the linked LF-strip lot
    # from the existing lot calibration mapping when available.
    calibration_lot = selected_lot
    session = db.scalar(select(CalibrationSession).where(
        CalibrationSession.lot_id == calibration_lot.id,
        CalibrationSession.analyte == "upsa",
        CalibrationSession.status == "closed",
    ).order_by(CalibrationSession.closed_at.desc()))

    if session is None:
        # Compatibility fallback: some Reader records expose the lot code rather than UUID.
        # Resolve the latest closed uPSA calibration whose QMS lot code matches the selected code.
        session = db.scalar(select(CalibrationSession).join(QmsLot, CalibrationSession.lot_id == QmsLot.id).where(
            CalibrationSession.analyte == "upsa",
            CalibrationSession.status == "closed",
            QmsLot.full_lot_record_code == selected_lot.full_lot_record_code,
        ).order_by(CalibrationSession.closed_at.desc()))
        if session is not None:
            calibration_lot = db.get(QmsLot, session.lot_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Nessuna calibrazione uPSA chiusa associata al lotto selezionato")

    metric_names = ["t_height", "t_area", "t_width", "t_fwhm", "c_height", "c_area", "c_width", "c_fwhm", "height_ratio", "area_ratio"]
    measurements = []

    # New workflow source: CalibrationPoint + CalibrationMeasurement.
    points = list(db.scalars(select(CalibrationPoint).where(
        CalibrationPoint.session_id == session.id,
        CalibrationPoint.optical_score == score,
    )))
    for point in points:
        for measurement in db.scalars(select(CalibrationMeasurement).where(
            CalibrationMeasurement.point_id == point.id,
            CalibrationMeasurement.status == "COMPLETED",
        )):
            row = {name: getattr(measurement, name, None) for name in metric_names}
            raw = measurement.raw_measurement or {}
            # Manual matrices may store the only available digital reference as T/C Area.
            if row.get("area_ratio") is None:
                for key in ("area_ratio", "t_c_area", "tc_area", "T_C_area"):
                    try:
                        if raw.get(key) is not None:
                            row["area_ratio"] = float(raw[key]); break
                    except (TypeError, ValueError):
                        pass
            row["source"] = measurement.source
            row["slot"] = point.concentration_slot
            if any(row[name] is not None for name in metric_names):
                measurements.append(row)

    # Legacy Reader source, only when workflow measurements are unavailable.
    if not measurements:
        for record in db.scalars(_records_query(session)):
            item = _measurement(record)
            if item and item["score"] == score:
                item["source"] = "READER_LEGACY"
                measurements.append(item)

    available_metrics = {}
    for name in metric_names:
        values = [float(row[name]) for row in measurements if row.get(name) is not None]
        if values:
            available_metrics[name] = {"mean": statistics.mean(values), **_aggregate(values)}

    if not measurements:
        raise HTTPException(status_code=404, detail="Calibrazione chiusa trovata, ma nessun riferimento disponibile per lo score ottico selezionato")
    if not available_metrics:
        raise HTTPException(status_code=409, detail="La calibrazione chiusa non contiene parametri digitali confrontabili, incluso T/C Area")

    return {
        "calibration_code": session.calibration_code,
        "selected_device_lot_id": selected_lot.id,
        "selected_device_lot_code": selected_lot.full_lot_record_code,
        "lot_id": calibration_lot.id,
        "lot_code": calibration_lot.full_lot_record_code,
        "closed_at": session.closed_at,
        "score": score,
        "replicate_count": len(measurements),
        "reference_source": "workflow",
        "metrics": available_metrics,
    }
@router.get("", response_model=list[CalibrationSessionDetail])
def list_calibrations(
    analyte: str | None = Query(default=None, pattern="^(upsa|uzinc)$"),
    status_filter: str | None = Query(default=None, alias="status", pattern="^(open|closed)$"),
    lot_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = select(CalibrationSession)
    if analyte is not None:
        query = query.where(CalibrationSession.analyte == analyte)
    if status_filter is not None:
        query = query.where(CalibrationSession.status == status_filter)
    if lot_id is not None:
        query = query.where(CalibrationSession.lot_id == lot_id)
    query = query.order_by(CalibrationSession.created_at.desc()).offset(offset).limit(limit)
    sessions = db.scalars(query).all()
    return [_detail(db, calibration) for calibration in sessions]


@router.patch("/{calibration_code}/lot", response_model=CalibrationSessionDetail)
def update_calibration_lot(calibration_code: str, payload: CalibrationLotUpdate, db: Session = Depends(get_db)):
    session = db.scalar(select(CalibrationSession).where(CalibrationSession.calibration_code == calibration_code))
    if session is None:
        raise HTTPException(status_code=404, detail="Calibration not found")
    lot = db.get(QmsLot, payload.lot_id)
    if lot is None:
        raise HTTPException(status_code=404, detail="Lotto non trovato")
    expected_lr = {"upsa": "LR-000122", "uzinc": "LR-000104"}.get(session.analyte)
    if expected_lr is None:
        raise HTTPException(status_code=409, detail="Analita della calibrazione non supportato")
    if lot.lr_document_code != expected_lr:
        raise HTTPException(status_code=409, detail=f"La calibrazione {session.analyte} richiede un lotto {expected_lr}")
    old_lot_code = session.lot.full_lot_record_code if session.lot is not None else None
    session.lot_id = lot.id
    for record in db.scalars(_records_query(session)):
        record.lot_id = lot.full_lot_record_code
        if session.analyte == "upsa":
            record.upsa_lot_id = lot.full_lot_record_code
        elif session.analyte == "uzinc":
            record.uzinc_lot_id = lot.full_lot_record_code
        raw = dict(record.raw_record or {})
        raw["lot_id"] = lot.full_lot_record_code
        raw["lot_uuid"] = str(lot.id)
        if session.analyte == "upsa": raw["upsa_lot_id"] = lot.full_lot_record_code
        if session.analyte == "uzinc": raw["uzinc_lot_id"] = lot.full_lot_record_code
        record.raw_record = raw
    audit = f"Lotto riassegnato da {old_lot_code or 'non disponibile'} a {lot.full_lot_record_code}"
    session.notes = (session.notes + "\n" + audit).strip() if session.notes else audit
    db.commit(); db.refresh(session)
    return _detail(db, session)


@router.delete("/{calibration_code}")
def delete_calibration(calibration_code: str, confirm: bool = Query(default=False), db: Session = Depends(get_db)):
    if not confirm:
        raise HTTPException(status_code=400, detail="Aggiungi confirm=true per confermare l'eliminazione")
    session = db.scalar(select(CalibrationSession).where(CalibrationSession.calibration_code == calibration_code))
    if session is None:
        raise HTTPException(status_code=404, detail="Calibration not found")
    records = list(db.scalars(_records_query(session)))
    deleted_acquisitions = len(records)
    for record in records:
        db.delete(record)
    db.delete(session)
    db.commit()
    return {"deleted": True, "calibration_code": calibration_code, "deleted_acquisitions": deleted_acquisitions}


@router.get("/{calibration_code}/acquisitions")
def calibration_acquisitions(calibration_code: str, db: Session = Depends(get_db)):
    session = db.scalar(
        select(CalibrationSession).where(
            CalibrationSession.calibration_code == calibration_code
        )
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Calibration not found")

    query = _records_query(session).order_by(
        TestRecord.optical_psa_score_0_4,
        TestRecord.replicate_number,
        TestRecord.captured_at,
    )
    acquisitions = []
    for record in db.scalars(query):
        acquisitions.append({
            "id": record.id,
            "sample_code": record.sample_code,
            "score": record.optical_psa_score_0_4,
            "replicate_number": record.replicate_number,
            "nominal_concentration_ug_ml": record.nominal_concentration_ug_ml,
            "captured_at": record.captured_at,
            "measurement": _measurement(record),
        })

    return {
        "calibration": _detail(db, session),
        "acquisitions": acquisitions,
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
    reader_count = db.scalar(select(func.count()).select_from(_records_query(session).subquery())) or 0
    workflow_count = _workflow_measurement_count(db, session)
    count = max(int(reader_count), workflow_count)
    if count < 1:
        raise HTTPException(status_code=409, detail="Salva almeno una replica prima di chiudere la calibrazione")
    session.status = "closed"; session.closed_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(session)
    return _detail(db, session)
