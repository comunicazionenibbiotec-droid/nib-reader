from sqlalchemy import text

from calibration_workflow_models import CalibrationMeasurement, CalibrationPlan, CalibrationPoint
from database import Base, engine


def migrate_calibration_workflow():
    Base.metadata.create_all(
        bind=engine,
        tables=[
            CalibrationPlan.__table__,
            CalibrationPoint.__table__,
            CalibrationMeasurement.__table__,
        ],
    )

    if engine.dialect.name == "postgresql":
        statements = [
            "ALTER TABLE calibration_points ADD COLUMN IF NOT EXISTS concentration_normalized_ng_ml DOUBLE PRECISION",
            "ALTER TABLE calibration_points ADD COLUMN IF NOT EXISTS skipped_replicates INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'COMPLETED'",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS skip_reason VARCHAR(200)",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS lab_l DOUBLE PRECISION",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS lab_a DOUBLE PRECISION",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS lab_b DOUBLE PRECISION",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS hue_lab DOUBLE PRECISION",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS chroma DOUBLE PRECISION",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS a_over_b DOUBLE PRECISION",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS saturation DOUBLE PRECISION",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS r_over_g DOUBLE PRECISION",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS b_over_g DOUBLE PRECISION",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS magenta_index DOUBLE PRECISION",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS delta_e_white DOUBLE PRECISION",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS luminance_ratio DOUBLE PRECISION",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS white_luminance_cv DOUBLE PRECISION",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS white_overexposed_fraction DOUBLE PRECISION",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS sample_clipped_fraction DOUBLE PRECISION",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS white_clipped_fraction DOUBLE PRECISION",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS sample_pixel_count INTEGER",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS white_pixel_count INTEGER",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS disc_detected BOOLEAN",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS detection_method VARCHAR(80)",
            "ALTER TABLE calibration_measurements ADD COLUMN IF NOT EXISTS uzinc_qc_status VARCHAR(30)",
            "CREATE INDEX IF NOT EXISTS ix_calibration_measurements_lab_a ON calibration_measurements (lab_a)",
            "CREATE INDEX IF NOT EXISTS ix_calibration_measurements_lab_b ON calibration_measurements (lab_b)",
            "CREATE INDEX IF NOT EXISTS ix_calibration_measurements_hue_lab ON calibration_measurements (hue_lab)",
            "CREATE INDEX IF NOT EXISTS ix_calibration_measurements_a_over_b ON calibration_measurements (a_over_b)",
            "CREATE INDEX IF NOT EXISTS ix_calibration_measurements_magenta_index ON calibration_measurements (magenta_index)",
            "CREATE INDEX IF NOT EXISTS ix_calibration_measurements_uzinc_qc_status ON calibration_measurements (uzinc_qc_status)",
            "UPDATE calibration_points SET concentration_normalized_ng_ml = CASE WHEN concentration_unit='ug/mL' THEN instrumental_concentration*1000 ELSE instrumental_concentration END WHERE concentration_normalized_ng_ml IS NULL",
        ]
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))

    print("ZENPSA DB: calibration workflow tables and uZinc metrics verified", flush=True)
