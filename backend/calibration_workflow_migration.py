from sqlalchemy import text
from calibration_workflow_models import CalibrationPlan,CalibrationPoint,CalibrationMeasurement
from database import Base,engine
def migrate_calibration_workflow():
    Base.metadata.create_all(bind=engine,tables=[CalibrationPlan.__table__,CalibrationPoint.__table__,CalibrationMeasurement.__table__])
    if engine.dialect.name=='postgresql':
        statements=[
          "ALTER TABLE calibration_points ADD COLUMN IF NOT EXISTS concentration_normalized_ng_ml DOUBLE PRECISION",
          "ALTER TABLE calibration_points ADD COLUMN IF NOT EXISTS skipped_replicates INTEGER NOT NULL DEFAULT 0",
          "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'COMPLETED'",
          "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS skip_reason VARCHAR(200)",
          "UPDATE calibration_points SET concentration_normalized_ng_ml = CASE WHEN concentration_unit='ug/mL' THEN instrumental_concentration*1000 ELSE instrumental_concentration END WHERE concentration_normalized_ng_ml IS NULL",
        ]
        with engine.begin() as c:
            for s in statements:c.execute(text(s))
    print('ZENPSA DB: calibration workflow tables verified',flush=True)
