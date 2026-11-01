import uuid
from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy import select
from sqlalchemy.orm import Session
from database import get_db
from calibration_models import CalibrationSession
from calibration_workflow_models import CalibrationPoint,CalibrationMeasurement
from calibration_workflow_schemas import PointCreate,MeasurementCreate
from qms_models import QmsLot
router=APIRouter(prefix='/calibration-workflows',tags=['calibration-workflows'])
def serialize_point(p):
 return {'id':p.id,'session_id':p.session_id,'optical_score':p.optical_score,'concentration_slot':p.concentration_slot,'instrumental_concentration':p.instrumental_concentration,'concentration_unit':p.concentration_unit,'planned_replicates':p.planned_replicates,'completed_replicates':p.completed_replicates,'next_replicate_number':p.completed_replicates+1 if p.completed_replicates<p.planned_replicates else None,'acquisition_mode':p.acquisition_mode,'status':p.status}
@router.post('/upsa/points',status_code=status.HTTP_201_CREATED)
def create_point(payload:PointCreate,db:Session=Depends(get_db)):
 lot=db.get(QmsLot,payload.lot_id)
 if not lot or lot.lr_document_code!='LR-000122': raise HTTPException(409,'La calibrazione uPSA richiede un lotto LR-000122')
 session=db.scalar(select(CalibrationSession).where(CalibrationSession.calibration_code==payload.calibration_code))
 if not session:
  session=CalibrationSession(calibration_code=payload.calibration_code,analyte='upsa',lot_id=lot.id,status='open');db.add(session);db.flush()
 elif session.lot_id!=lot.id: raise HTTPException(409,'Il codice calibrazione è associato a un altro lotto')
 existing=db.scalar(select(CalibrationPoint).where(CalibrationPoint.session_id==session.id,CalibrationPoint.optical_score==payload.optical_score,CalibrationPoint.concentration_slot==payload.concentration_slot))
 if existing: raise HTTPException(409,'Punto ottico/slot già esistente')
 p=CalibrationPoint(session_id=session.id,**payload.model_dump(exclude={'calibration_code','lot_id'}));db.add(p);db.commit();db.refresh(p);return serialize_point(p)
@router.get('/points/{point_id}')
def get_point(point_id:uuid.UUID,db:Session=Depends(get_db)):
 p=db.get(CalibrationPoint,point_id)
 if not p: raise HTTPException(404,'Punto calibrazione non trovato')
 out=serialize_point(p);out['measurements']=[{'id':m.id,'replicate_number':m.replicate_number,'source':m.source,'record_id':m.record_id,'t_height':m.t_height,'t_area':m.t_area,'c_height':m.c_height,'c_area':m.c_area,'height_ratio':m.height_ratio,'area_ratio':m.area_ratio} for m in db.scalars(select(CalibrationMeasurement).where(CalibrationMeasurement.point_id==p.id).order_by(CalibrationMeasurement.replicate_number))];return out
@router.post('/points/{point_id}/measurements',status_code=status.HTTP_201_CREATED)
def add_measurement(point_id:uuid.UUID,payload:MeasurementCreate,db:Session=Depends(get_db)):
 p=db.get(CalibrationPoint,point_id)
 if not p: raise HTTPException(404,'Punto calibrazione non trovato')
 if p.status!='IN_PROGRESS': raise HTTPException(409,'Punto calibrazione non attivo')
 if payload.replicate_number!=p.completed_replicates+1: raise HTTPException(409,f'Replica attesa: {p.completed_replicates+1}')
 if payload.replicate_number>p.planned_replicates: raise HTTPException(409,'Numero repliche superato')
 m=CalibrationMeasurement(point_id=p.id,**payload.model_dump());db.add(m);p.completed_replicates+=1
 if p.completed_replicates>=p.planned_replicates:p.status='COMPLETED'
 db.commit();db.refresh(m);return {'id':m.id,'point':serialize_point(p)}
@router.get('/sessions/{calibration_code}/matrix')
def matrix(calibration_code:str,db:Session=Depends(get_db)):
 s=db.scalar(select(CalibrationSession).where(CalibrationSession.calibration_code==calibration_code))
 if not s: raise HTTPException(404,'Calibrazione non trovata')
 rows=[]
 for p in db.scalars(select(CalibrationPoint).where(CalibrationPoint.session_id==s.id).order_by(CalibrationPoint.optical_score,CalibrationPoint.concentration_slot)):
  item=serialize_point(p);item['measurements']=[{'replicate_number':m.replicate_number,'source':m.source,'t_height':m.t_height,'t_area':m.t_area,'c_height':m.c_height,'c_area':m.c_area,'height_ratio':m.height_ratio,'area_ratio':m.area_ratio,'record_id':m.record_id} for m in db.scalars(select(CalibrationMeasurement).where(CalibrationMeasurement.point_id==p.id).order_by(CalibrationMeasurement.replicate_number))];rows.append(item)
 return {'calibration_code':calibration_code,'analyte':'upsa','points':rows}
