from sqlalchemy import text
from database import engine

def migrate_urine_fields() -> None:
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE test_records ADD COLUMN IF NOT EXISTS urine_color VARCHAR(30)"))
        connection.execute(text("ALTER TABLE test_records ADD COLUMN IF NOT EXISTS urine_turbid BOOLEAN NOT NULL DEFAULT FALSE"))
    print("ZENPSA DB: urine fields migration verified", flush=True)
