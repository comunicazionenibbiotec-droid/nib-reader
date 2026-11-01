import uuid
from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from database import get_db
from calibration_models import CalibrationSession
from calibration_workflow_models import CalibrationPlan,CalibrationPoint,CalibrationMeasurement
from calibration_workflow_schemas import PlanCreate,PointCreate,MeasurementCreate,SkipCreate
from qms_models import QmsLot
router=APIRouter(prefix='/calibration-workflows',tags=['calibration-workflows'])
def normalized(value,unit):return round(value*1000 if unit=='ug/mL' else value,6)
def next_rep(db,p):
 used=set(db.scalars(select(CalibrationMeasurement.replicate_number).where(CalibrationMeasurement.point_id==p.id)))
 return next((n for n in range(1,p.planned_replicates+1) if n not in used),None)
def serialize(db,p):
 return {'id':p.id,'session_id':p.session_id,'optical_score':p.optical_score,'concentration_slot':p.concentration_slot,'instrumental_concentration':p.instrumental_concentration,'concentration_unit':p.concentration_unit,'planned_replicates':p.planned_replicates,'completed_replicates':p.completed_replicates,'skipped_replicates':p.skipped_replicates,'next_replicate_number':next_rep(db,p),'acquisition_mode':p.acquisition_mode,'status':p.status}
def require_lot(db,lot_id):
 lot=db.get(QmsLot,lot_id)
 if not lot or lot.lr_document_code!='LR-000122':raise HTTPException(409,'La calibrazione uPSA richiede un lotto LR-000122')
 return lot
def session_for(db,code,lot):
 s=db.scalar(select(CalibrationSession).where(CalibrationSession.calibration_code==code))
 if not s:s=CalibrationSession(calibration_code=code,analyte='upsa',lot_id=lot.id,status='open');db.add(s);db.flush()
 elif s.lot_id!=lot.id:raise HTTPException(409,'Il codice calibrazione è associato a un altro lotto')
 return s
@router.post('/upsa/plans',status_code=201)
def create_plan(payload:PlanCreate,db:Session=Depends(get_db)):
 lot=require_lot(db,payload.lot_id);s=session_for(db,payload.calibration_code,lot)
 plan=db.scalar(select(CalibrationPlan).where(CalibrationPlan.session_id==s.id))
 if plan:plan.expected_concentrations=payload.expected_concentrations;plan.default_replicates=payload.default_replicates
 else:plan=CalibrationPlan(session_id=s.id,expected_concentrations=payload.expected_concentrations,default_replicates=payload.default_replicates);db.add(plan)
 db.commit();return {'calibration_code':s.calibration_code,'lot_id':s.lot_id,'analyte':'upsa','expected_concentrations':plan.expected_concentrations,'default_replicates':plan.default_replicates}
@router.get('/upsa/plans/{code}')
def get_plan(code:str,db:Session=Depends(get_db)):
 s=db.scalar(select(CalibrationSession).where(CalibrationSession.calibration_code==code))
 if not s:raise HTTPException(404,'Calibrazione non trovata')
 p=db.scalar(select(CalibrationPlan).where(CalibrationPlan.session_id==s.id));points=list(db.scalars(select(CalibrationPoint).where(CalibrationPoint.session_id==s.id)))
 return {'calibration_code':code,'lot_id':s.lot_id,'analyte':'upsa','expected_concentrations':p.expected_concentrations if p else None,'default_replicates':p.default_replicates if p else None,'points':[serialize(db,x) for x in points]}
@router.post('/upsa/points',status_code=201)
def create_point(payload:PointCreate,db:Session=Depends(get_db)):
 lot=require_lot(db,payload.lot_id);s=session_for(db,payload.calibration_code,lot);norm=normalized(payload.instrumental_concentration,payload.concentration_unit)
 duplicate=db.scalar(select(CalibrationPoint).where(CalibrationPoint.session_id==s.id,CalibrationPoint.optical_score==payload.optical_score,func.abs(CalibrationPoint.concentration_normalized_ng_ml-norm)<0.000001))
 if duplicate:
  out=serialize(db,duplicate);out['duplicate']=True;out['message']='Concentrazione e lettura ottica già acquisite';db.commit();return out
 slot=db.scalar(select(CalibrationPoint).where(CalibrationPoint.session_id==s.id,CalibrationPoint.optical_score==payload.optical_score,CalibrationPoint.concentration_slot==payload.concentration_slot))
 if slot:raise HTTPException(409,'Lo slot selezionato è già occupato per questo score ottico')
 p=CalibrationPoint(session_id=s.id,optical_score=payload.optical_score,concentration_slot=payload.concentration_slot,instrumental_concentration=payload.instrumental_concentration,concentration_unit=payload.concentration_unit,concentration_normalized_ng_ml=norm,planned_replicates=payload.planned_replicates,acquisition_mode=payload.acquisition_mode);db.add(p);db.commit();db.refresh(p);return serialize(db,p)
@router.get('/points/{point_id}')
def get_point(point_id:uuid.UUID,db:Session=Depends(get_db)):
 p=db.get(CalibrationPoint,point_id)
 if not p:raise HTTPException(404,'Punto non trovato')
 out=serialize(db,p);out['measurements']=[{'id':m.id,'replicate_number':m.replicate_number,'status':m.status,'source':m.source,'record_id':m.record_id,'skip_reason':m.skip_reason,'t_height':m.t_height,'t_area':m.t_area,'c_height':m.c_height,'c_area':m.c_area,'height_ratio':m.height_ratio,'area_ratio':m.area_ratio} for m in db.scalars(select(CalibrationMeasurement).where(CalibrationMeasurement.point_id==p.id).order_by(CalibrationMeasurement.replicate_number))];return out
@router.post('/points/{point_id}/measurements',status_code=201)
def add_measurement(point_id:uuid.UUID,payload:MeasurementCreate,db:Session=Depends(get_db)):
 p=db.get(CalibrationPoint,point_id)
 if not p:raise HTTPException(404,'Punto non trovato')
 expected=next_rep(db,p)
 if expected is None:raise HTTPException(409,'Punto completato')
 if payload.replicate_number!=expected:raise HTTPException(409,f'Replica attesa: {expected}')
 m=CalibrationMeasurement(point_id=p.id,status='COMPLETED',**payload.model_dump());db.add(m);p.completed_replicates+=1
 db.flush();p.status='COMPLETED' if next_rep(db,p) is None else 'IN_PROGRESS';db.commit();return {'id':m.id,'point':serialize(db,p)}
@router.post('/points/{point_id}/skip',status_code=201)
def skip(point_id:uuid.UUID,payload:SkipCreate,db:Session=Depends(get_db)):
 p=db.get(CalibrationPoint,point_id)
 if not p:raise HTTPException(404,'Punto non trovato')
 expected=next_rep(db,p)
 if expected is None:raise HTTPException(409,'Punto completato')
 m=CalibrationMeasurement(point_id=p.id,replicate_number=expected,source='READER',status='SKIPPED',skip_reason=payload.reason,raw_measurement={});db.add(m);p.skipped_replicates+=1
 db.flush();p.status='COMPLETED' if next_rep(db,p) is None else 'IN_PROGRESS';db.commit();return {'id':m.id,'point':serialize(db,p)}
@router.get('/sessions/{code}/matrix')
def matrix(code:str,db:Session=Depends(get_db)):
 s=db.scalar(select(CalibrationSession).where(CalibrationSession.calibration_code==code))
 if not s:raise HTTPException(404,'Calibrazione non trovata')
 return {'calibration_code':code,'analyte':'upsa','points':[get_point(p.id,db) for p in db.scalars(select(CalibrationPoint).where(CalibrationPoint.session_id==s.id).order_by(CalibrationPoint.optical_score,CalibrationPoint.concentration_slot))]}
