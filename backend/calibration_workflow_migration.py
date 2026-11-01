from calibration_workflow_models import CalibrationPoint,CalibrationMeasurement
from database import Base,engine
def migrate_calibration_workflow():
 Base.metadata.create_all(bind=engine,tables=[CalibrationPoint.__table__,CalibrationMeasurement.__table__])
 print('ZENPSA DB: calibration workflow tables verified',flush=True)
