import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from database import get_db
from calibration_models import CalibrationSession
from calibration_workflow_models import CalibrationPlan, CalibrationPoint, CalibrationMeasurement
from calibration_workflow_schemas import PlanCreate, PointCreate, MeasurementCreate, UzincMeasurementUpdate, SkipCreate
from pydantic import BaseModel, Field
from qms_models import QmsLot

router = APIRouter(prefix='/calibration-workflows', tags=['calibration-workflows'])

class UzincPointCreate(BaseModel):
    calibration_code: str = Field(min_length=1, max_length=80)
    lot_id: uuid.UUID
    optical_score: int = Field(ge=0, le=4)
    concentration_slot: str = Field(pattern='^[AB]$')
    instrumental_concentration: float = Field(ge=0)
    concentration_unit: str = 'ug/mL'
    planned_replicates: int = Field(ge=1, le=10)
    acquisition_mode: str = 'MANUAL'

def normalized(value, unit): return round(value * 1000 if unit == 'ug/mL' else value, 6)
def next_rep(db, p):
    used = set(db.scalars(select(CalibrationMeasurement.replicate_number).where(CalibrationMeasurement.point_id == p.id)))
    return next((n for n in range(1, p.planned_replicates + 1) if n not in used), None)
def serialize(db, p):
    return {'id':p.id,'session_id':p.session_id,'optical_score':p.optical_score,'concentration_slot':p.concentration_slot,'instrumental_concentration':p.instrumental_concentration,'concentration_unit':p.concentration_unit,'planned_replicates':p.planned_replicates,'completed_replicates':p.completed_replicates,'skipped_replicates':p.skipped_replicates,'next_replicate_number':next_rep(db,p),'acquisition_mode':p.acquisition_mode,'status':p.status}
def serialize_measurement(m):
    raw = m.raw_measurement or {}
    image_url = raw.get('image_url') or raw.get('preview_url') or raw.get('signed_url') or raw.get('r2_signed_url')
    return {
        'id': m.id,
        'replicate_number': m.replicate_number,
        'status': m.status,
        'source': m.source,
        'record_id': m.record_id,
        'skip_reason': m.skip_reason,
        # uPSA metrics.
        't_height': m.t_height,
        't_area': m.t_area,
        't_width': m.t_width,
        't_fwhm': m.t_fwhm,
        'c_height': m.c_height,
        'c_area': m.c_area,
        'c_width': m.c_width,
        'c_fwhm': m.c_fwhm,
        'height_ratio': m.height_ratio,
        'area_ratio': m.area_ratio,
        # uZinc metrics.
        'lab_l': m.lab_l,
        'lab_a': m.lab_a,
        'lab_b': m.lab_b,
        'hue_lab': m.hue_lab,
        'chroma': m.chroma,
        'a_over_b': m.a_over_b,
        'saturation': m.saturation,
        'r_over_g': m.r_over_g,
        'b_over_g': m.b_over_g,
        'magenta_index': m.magenta_index,
        'delta_e_white': m.delta_e_white,
        'luminance_ratio': m.luminance_ratio,
        # uZinc QC.
        'white_luminance_cv': m.white_luminance_cv,
        'white_overexposed_fraction': m.white_overexposed_fraction,
        'sample_clipped_fraction': m.sample_clipped_fraction,
        'white_clipped_fraction': m.white_clipped_fraction,
        'sample_pixel_count': m.sample_pixel_count,
        'white_pixel_count': m.white_pixel_count,
        'disc_detected': m.disc_detected,
        'detection_method': m.detection_method,
        'uzinc_qc_status': m.uzinc_qc_status,
        'image_url': image_url,
        'raw_measurement': raw,
    }
def require_lot(db, lot_id):
    lot = db.get(QmsLot, lot_id)
    if not lot or lot.lr_document_code != 'LR-000122': raise HTTPException(409, 'La calibrazione uPSA richiede un lotto LR-000122')
    return lot
def session_for(db, code, lot):
    s = db.scalar(select(CalibrationSession).where(CalibrationSession.calibration_code == code))
    if not s: s=CalibrationSession(calibration_code=code,analyte='upsa',lot_id=lot.id,status='open'); db.add(s); db.flush()
    elif s.lot_id != lot.id: raise HTTPException(409, 'Il codice calibrazione è associato a un altro lotto')
    return s

@router.post('/upsa/plans', status_code=201)
def create_plan(payload: PlanCreate, db: Session = Depends(get_db)):
    lot=require_lot(db,payload.lot_id); s=session_for(db,payload.calibration_code,lot)
    plan=db.scalar(select(CalibrationPlan).where(CalibrationPlan.session_id==s.id))
    if plan: plan.expected_concentrations=payload.expected_concentrations; plan.default_replicates=payload.default_replicates
    else: plan=CalibrationPlan(session_id=s.id,expected_concentrations=payload.expected_concentrations,default_replicates=payload.default_replicates); db.add(plan)
    db.commit(); return {'calibration_code':s.calibration_code,'lot_id':s.lot_id,'analyte':'upsa','expected_concentrations':plan.expected_concentrations,'default_replicates':plan.default_replicates,'status':s.status}

@router.get('/upsa/plans/{code}')
def get_plan(code: str, db: Session = Depends(get_db)):
    s=db.scalar(select(CalibrationSession).where(CalibrationSession.calibration_code==code))
    if not s: raise HTTPException(404,'Calibrazione non trovata')
    p=db.scalar(select(CalibrationPlan).where(CalibrationPlan.session_id==s.id)); points=list(db.scalars(select(CalibrationPoint).where(CalibrationPoint.session_id==s.id)))
    return {'calibration_code':code,'lot_id':s.lot_id,'analyte':'upsa','status':s.status,'expected_concentrations':p.expected_concentrations if p else None,'default_replicates':p.default_replicates if p else None,'points':[serialize(db,x) for x in points]}

@router.post('/upsa/points', status_code=201)
def create_point(payload: PointCreate, db: Session = Depends(get_db)):
    lot=require_lot(db,payload.lot_id); s=session_for(db,payload.calibration_code,lot)
    if s.status=='closed': raise HTTPException(409,'La calibrazione è chiusa. Premi Modifica prima di aggiornare la matrice.')
    norm=normalized(payload.instrumental_concentration,payload.concentration_unit)
    duplicate=db.scalar(select(CalibrationPoint).where(CalibrationPoint.session_id==s.id,CalibrationPoint.optical_score==payload.optical_score,func.abs(CalibrationPoint.concentration_normalized_ng_ml-norm)<0.000001))
    if duplicate:
        out=serialize(db,duplicate); out['duplicate']=True; out['message']='Concentrazione e lettura ottica già acquisite'; db.commit(); return out
    slot=db.scalar(select(CalibrationPoint).where(CalibrationPoint.session_id==s.id,CalibrationPoint.optical_score==payload.optical_score,CalibrationPoint.concentration_slot==payload.concentration_slot))
    if slot: raise HTTPException(409,'Lo slot selezionato è già occupato per questo score ottico')
    p=CalibrationPoint(session_id=s.id,optical_score=payload.optical_score,concentration_slot=payload.concentration_slot,instrumental_concentration=payload.instrumental_concentration,concentration_unit=payload.concentration_unit,concentration_normalized_ng_ml=norm,planned_replicates=payload.planned_replicates,acquisition_mode=payload.acquisition_mode); db.add(p); db.commit(); db.refresh(p); return serialize(db,p)

@router.get('/points/{point_id}')
def get_point(point_id: uuid.UUID, db: Session = Depends(get_db)):
    p=db.get(CalibrationPoint,point_id)
    if not p: raise HTTPException(404,'Punto non trovato')
    out=serialize(db,p); out['measurements']=[serialize_measurement(m) for m in db.scalars(select(CalibrationMeasurement).where(CalibrationMeasurement.point_id==p.id).order_by(CalibrationMeasurement.replicate_number))]; return out

@router.post('/points/{point_id}/measurements', status_code=201)
def add_measurement(point_id: uuid.UUID, payload: MeasurementCreate, db: Session = Depends(get_db)):
    p=db.get(CalibrationPoint,point_id)
    if not p: raise HTTPException(404,'Punto non trovato')
    s=db.get(CalibrationSession,p.session_id)
    if s and s.status=='closed': raise HTTPException(409,'La calibrazione è chiusa. Premi Modifica prima di aggiungere misure.')
    expected=next_rep(db,p)
    if expected is None: raise HTTPException(409,'Punto completato')
    if payload.replicate_number!=expected: raise HTTPException(409,f'Replica attesa: {expected}')
    m=CalibrationMeasurement(point_id=p.id,status='COMPLETED',**payload.model_dump()); db.add(m); p.completed_replicates+=1
    db.flush(); p.status='COMPLETED' if next_rep(db,p) is None else 'IN_PROGRESS'; db.commit(); return {'id':m.id,'point':serialize(db,p)}

@router.post('/points/{point_id}/skip', status_code=201)
def skip(point_id: uuid.UUID, payload: SkipCreate, db: Session = Depends(get_db)):
    p=db.get(CalibrationPoint,point_id)
    if not p: raise HTTPException(404,'Punto non trovato')
    expected=next_rep(db,p)
    if expected is None: raise HTTPException(409,'Punto completato')
    m=CalibrationMeasurement(point_id=p.id,replicate_number=expected,source='READER',status='SKIPPED',skip_reason=payload.reason,raw_measurement={}); db.add(m); p.skipped_replicates+=1
    db.flush(); p.status='COMPLETED' if next_rep(db,p) is None else 'IN_PROGRESS'; db.commit(); return {'id':m.id,'point':serialize(db,p)}

@router.get('/sessions/{code}/matrix')
def matrix(code: str, db: Session = Depends(get_db)):
    s=db.scalar(select(CalibrationSession).where(CalibrationSession.calibration_code==code))
    if not s: raise HTTPException(404,'Calibrazione non trovata')
    points=[get_point(p.id,db) for p in db.scalars(select(CalibrationPoint).where(CalibrationPoint.session_id==s.id).order_by(CalibrationPoint.optical_score,CalibrationPoint.concentration_slot))]
    return {'calibration_code':code,'analyte':s.analyte,'status':s.status,'opened_at':s.opened_at,'closed_at':s.closed_at,'points':points}

@router.post('/sessions/{code}/close')
def close_workflow(code: str, db: Session = Depends(get_db)):
    s=db.scalar(select(CalibrationSession).where(CalibrationSession.calibration_code==code))
    if not s: raise HTTPException(404,'Calibrazione non trovata')
    count=db.scalar(select(func.count()).select_from(CalibrationMeasurement).join(CalibrationPoint,CalibrationMeasurement.point_id==CalibrationPoint.id).where(CalibrationPoint.session_id==s.id,CalibrationMeasurement.status=='COMPLETED')) or 0
    if count < 1: raise HTTPException(409,'Salva almeno una replica della matrice prima di chiudere')
    s.status='closed'; s.closed_at=datetime.now(timezone.utc); db.commit(); return {'calibration_code':code,'status':s.status,'closed_at':s.closed_at,'measurement_count':int(count)}

@router.post('/sessions/{code}/reopen')
def reopen_workflow(code: str, db: Session = Depends(get_db)):
    s=db.scalar(select(CalibrationSession).where(CalibrationSession.calibration_code==code))
    if not s: raise HTTPException(404,'Calibrazione non trovata')
    s.status='open'; s.closed_at=None; db.commit(); return {'calibration_code':code,'status':s.status}


@router.post('/uzinc/plans', status_code=201)
def create_uzinc_plan(payload: PlanCreate, db: Session = Depends(get_db)):
    lot = db.get(QmsLot, payload.lot_id)
    if not lot or lot.lr_document_code != 'LR-000104':
        raise HTTPException(409, 'La calibrazione uZinc richiede un lotto LR-000104')
    s = db.scalar(select(CalibrationSession).where(CalibrationSession.calibration_code == payload.calibration_code))
    if not s:
        s = CalibrationSession(calibration_code=payload.calibration_code, analyte='uzinc', lot_id=lot.id, status='open'); db.add(s); db.flush()
    elif s.analyte != 'uzinc' or s.lot_id != lot.id:
        raise HTTPException(409, 'Codice calibrazione gia associato a un altro analita o lotto')
    plan = db.scalar(select(CalibrationPlan).where(CalibrationPlan.session_id == s.id))
    if plan:
        plan.expected_concentrations=payload.expected_concentrations; plan.default_replicates=payload.default_replicates
    else:
        plan=CalibrationPlan(session_id=s.id, expected_concentrations=payload.expected_concentrations, default_replicates=payload.default_replicates); db.add(plan)
    db.commit()
    return {'calibration_code':s.calibration_code,'lot_id':s.lot_id,'analyte':'uzinc','expected_concentrations':plan.expected_concentrations,'default_replicates':plan.default_replicates,'status':s.status}

@router.post('/uzinc/points', status_code=201)
def create_uzinc_point(payload: UzincPointCreate, db: Session = Depends(get_db)):
    code=payload.calibration_code; lot_id=payload.lot_id; idx=payload.optical_score; slot=payload.concentration_slot; conc=payload.instrumental_concentration; reps=payload.planned_replicates
    s=db.scalar(select(CalibrationSession).where(CalibrationSession.calibration_code==code,CalibrationSession.analyte=='uzinc'))
    if not s or s.lot_id != lot_id: raise HTTPException(404,'Sessione uZinc non trovata')
    if s.status=='closed': raise HTTPException(409,'La calibrazione e chiusa. Premi Modifica prima di aggiornare la matrice.')
    existing=db.scalar(select(CalibrationPoint).where(CalibrationPoint.session_id==s.id,CalibrationPoint.optical_score==idx,CalibrationPoint.concentration_slot==slot))
    if existing:
        out=serialize(db,existing); out['duplicate']=True; return out
    p=CalibrationPoint(session_id=s.id,optical_score=idx,concentration_slot=slot,instrumental_concentration=conc,concentration_unit=payload.concentration_unit,concentration_normalized_ng_ml=conc*1000 if payload.concentration_unit=='ug/mL' else conc,planned_replicates=reps,acquisition_mode=payload.acquisition_mode)
    db.add(p); db.commit(); db.refresh(p); return serialize(db,p)



@router.patch('/uzinc/measurements/{measurement_id}')
def update_uzinc_measurement(measurement_id: uuid.UUID, payload: UzincMeasurementUpdate, db: Session = Depends(get_db)):
    measurement = db.get(CalibrationMeasurement, measurement_id)
    if not measurement:
        raise HTTPException(404, 'Misura non trovata')
    point = db.get(CalibrationPoint, measurement.point_id)
    session = db.get(CalibrationSession, point.session_id) if point else None
    if not point or not session or session.analyte != 'uzinc':
        raise HTTPException(409, 'La misura non appartiene a una calibrazione uZinc')
    if session.status == 'closed':
        raise HTTPException(409, 'La calibrazione e chiusa. Riaprila prima di modificare la replica.')
    if str(measurement.source or '').upper() not in ('MANUAL',):
        raise HTTPException(409, 'Le acquisizioni Reader sono in sola lettura e non possono essere modificate manualmente')

    changes = payload.model_dump(exclude_unset=True)
    raw_patch = changes.pop('raw_measurement', None)
    if raw_patch is not None:
        current_raw = dict(measurement.raw_measurement or {})
        current_raw.update(raw_patch)
        current_raw['manual_editor_updated_at'] = datetime.now(timezone.utc).isoformat()
        measurement.raw_measurement = current_raw
    for field, value in changes.items():
        setattr(measurement, field, value)

    if measurement.a_over_b is None and measurement.lab_a is not None and measurement.lab_b not in (None, 0):
        measurement.a_over_b = measurement.lab_a / measurement.lab_b
    db.commit()
    db.refresh(measurement)
    return serialize_measurement(measurement)

@router.post('/uzinc/points/{point_id}/measurements', status_code=201)
def add_uzinc_measurement(point_id: uuid.UUID, payload: MeasurementCreate, db: Session = Depends(get_db)):
    p=db.get(CalibrationPoint,point_id)
    if not p: raise HTTPException(404,'Punto non trovato')
    s=db.get(CalibrationSession,p.session_id)
    if not s or s.analyte!='uzinc': raise HTTPException(409,'Il punto non appartiene a una calibrazione uZinc')
    expected=next_rep(db,p)
    if expected is None: raise HTTPException(409,'Punto completato')
    if payload.replicate_number != expected: raise HTTPException(409,f'Replica attesa: {expected}')
    m=CalibrationMeasurement(point_id=p.id,status='COMPLETED',**payload.model_dump()); db.add(m); p.completed_replicates+=1; db.flush(); p.status='COMPLETED' if next_rep(db,p) is None else 'IN_PROGRESS'; db.commit(); return {'id':m.id,'point':serialize(db,p)}
