from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from database import get_db
from calibration_models import CalibrationSession
from calibration_schemas import CalibrationSessionCreate, CalibrationSessionDetail
from record_models import TestRecord

router = APIRouter(prefix="/calibrations", tags=["calibrations"])


def _detail(db: Session, session: CalibrationSession) -> dict:
    count = db.scalar(
        select(func.count(TestRecord.id)).where(
            TestRecord.record_purpose == "calibration",
            TestRecord.calibration_code == session.calibration_code,
        )
    ) or 0
    return {
        "id": session.id,
        "calibration_code": session.calibration_code,
        "analyte": session.analyte,
        "status": session.status,
        "opened_at": session.opened_at,
        "closed_at": session.closed_at,
        "notes": session.notes,
        "acquisition_count": int(count),
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }


@router.post("", response_model=CalibrationSessionDetail, status_code=status.HTTP_201_CREATED)
def open_calibration(payload: CalibrationSessionCreate, db: Session = Depends(get_db)):
    code = payload.calibration_code.strip()
    existing = db.scalar(select(CalibrationSession).where(CalibrationSession.calibration_code == code))
    if existing:
        if existing.status == "closed":
            raise HTTPException(status_code=409, detail="Calibration is already closed")
        return _detail(db, existing)
    session = CalibrationSession(calibration_code=code, analyte=payload.analyte, notes=payload.notes)
    db.add(session)
    db.commit()
    db.refresh(session)
    return _detail(db, session)


@router.get("/{calibration_code}", response_model=CalibrationSessionDetail)
def get_calibration(calibration_code: str, db: Session = Depends(get_db)):
    session = db.scalar(select(CalibrationSession).where(CalibrationSession.calibration_code == calibration_code))
    if not session:
        raise HTTPException(status_code=404, detail="Calibration not found")
    return _detail(db, session)


@router.post("/{calibration_code}/close", response_model=CalibrationSessionDetail)
def close_calibration(calibration_code: str, db: Session = Depends(get_db)):
    session = db.scalar(select(CalibrationSession).where(CalibrationSession.calibration_code == calibration_code))
    if not session:
        raise HTTPException(status_code=404, detail="Calibration not found")
    count = db.scalar(select(func.count(TestRecord.id)).where(
        TestRecord.record_purpose == "calibration",
        TestRecord.calibration_code == calibration_code,
    )) or 0
    if count < 1:
        raise HTTPException(status_code=409, detail="Save at least one acquisition before closing")
    session.status = "closed"
    session.closed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)
    return _detail(db, session)
