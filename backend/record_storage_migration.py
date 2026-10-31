from sqlalchemy import text
from database import engine

def migrate_record_storage_columns() -> None:
    statements = [
      "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS sample_condition VARCHAR(20)",
      "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS acquisition_pair_id VARCHAR(80)",
      "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS parent_record_id UUID",
      "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS dilution_factor DOUBLE PRECISION",
      "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS reference_urine_volume_ml DOUBLE PRECISION",
      "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS target_mix_volume_ul DOUBLE PRECISION",
      "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS sample_volume_ul DOUBLE PRECISION",
      "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS solvent_volume_ul DOUBLE PRECISION",
      "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS image_storage_status VARCHAR(20) NOT NULL DEFAULT 'NOT_REQUESTED'",
      "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS image_object_key VARCHAR(500)",
      "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS image_filename VARCHAR(200)",
      "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS image_content_type VARCHAR(80)",
      "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS image_size_bytes INTEGER",
      "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS image_sha256 VARCHAR(64)",
      "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS image_uploaded_at TIMESTAMPTZ",
      "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS image_upload_error TEXT",
      "CREATE INDEX IF NOT EXISTS ix_test_records_sample_condition ON test_records (sample_condition)",
      "CREATE INDEX IF NOT EXISTS ix_test_records_acquisition_pair_id ON test_records (acquisition_pair_id)",
      "CREATE INDEX IF NOT EXISTS ix_test_records_image_storage_status ON test_records (image_storage_status)",
    ]
    with engine.begin() as connection:
        for statement in statements: connection.execute(text(statement))
    print("ZENPSA DB: record storage migration verified", flush=True)
