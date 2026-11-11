from sqlalchemy import text
from calibration_workflow_models import CalibrationMeasurement, CalibrationPlan, CalibrationPoint
from database import Base, engine

def migrate_calibration_workflow():
    Base.metadata.create_all(bind=engine,tables=[CalibrationPlan.__table__,CalibrationPoint.__table__,CalibrationMeasurement.__table__])
    if engine.dialect.name == 'postgresql':
        fields = {
            'lab_l':'DOUBLE PRECISION','lab_a':'DOUBLE PRECISION','lab_b':'DOUBLE PRECISION','hue_lab':'DOUBLE PRECISION',
            'chroma':'DOUBLE PRECISION','a_over_b':'DOUBLE PRECISION','saturation':'DOUBLE PRECISION','r_over_g':'DOUBLE PRECISION',
            'b_over_g':'DOUBLE PRECISION','magenta_index':'DOUBLE PRECISION','delta_e_white':'DOUBLE PRECISION','luminance_ratio':'DOUBLE PRECISION',
            'white_luminance_cv':'DOUBLE PRECISION','white_overexposed_fraction':'DOUBLE PRECISION','sample_clipped_fraction':'DOUBLE PRECISION',
            'white_clipped_fraction':'DOUBLE PRECISION','sample_pixel_count':'INTEGER','white_pixel_count':'INTEGER','disc_detected':'BOOLEAN',
            'detection_method':'VARCHAR(80)','uzinc_qc_status':'VARCHAR(30)'
        }
        statements=[f'ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS {name} {sqltype}' for name,sqltype in fields.items()]
        statements += [
            'CREATE INDEX IF NOT EXISTS ix_calibration_measurements_lab_a ON calibration_measurements (lab_a)',
            'CREATE INDEX IF NOT EXISTS ix_calibration_measurements_lab_b ON calibration_measurements (lab_b)',
            'CREATE INDEX IF NOT EXISTS ix_calibration_measurements_hue_lab ON calibration_measurements (hue_lab)',
            'CREATE INDEX IF NOT EXISTS ix_calibration_measurements_a_over_b ON calibration_measurements (a_over_b)',
            'CREATE INDEX IF NOT EXISTS ix_calibration_measurements_magenta_index ON calibration_measurements (magenta_index)',
            'CREATE INDEX IF NOT EXISTS ix_calibration_measurements_uzinc_qc_status ON calibration_measurements (uzinc_qc_status)'
        ]
        with engine.begin() as connection:
            for statement in statements: connection.execute(text(statement))
    print('ZENPSA DB: calibration workflow and uZinc manual editor fields verified',flush=True)
