import os
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def _database_url() -> str:
    value = os.getenv("DATABASE_URL", "sqlite:///./zenpsa_local.db")
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    return value


DATABASE_URL = _database_url()
CONNECT_ARGS = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=CONNECT_ARGS)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_database_tables() -> None:
    from record_models import TestRecord
    Base.metadata.create_all(bind=engine)
    if not DATABASE_URL.startswith("sqlite"):
        migrate_record_classification_columns()


def migrate_record_classification_columns() -> None:
    statements = [
        "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS record_purpose VARCHAR(30) NOT NULL DEFAULT 'unclassified'",
        "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS study_code VARCHAR(80)",
        "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS calibration_code VARCHAR(80)",
        "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS calibration_analyte VARCHAR(20)",
        "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS nominal_concentration_ug_ml DOUBLE PRECISION",
        "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS replicate_number INTEGER",
        "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS upsa_lot_id VARCHAR(80)",
        "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS uzinc_lot_id VARCHAR(80)",
        "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS upsa_corrected_ug_ml DOUBLE PRECISION",
        "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS upsa_absolute_quantity_ug DOUBLE PRECISION",
        "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS uzinc_corrected_ug_ml DOUBLE PRECISION",
        "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS uzinc_absolute_quantity_ug DOUBLE PRECISION",
        "CREATE INDEX IF NOT EXISTS ix_test_records_record_purpose ON test_records (record_purpose)",
        "CREATE INDEX IF NOT EXISTS ix_test_records_calibration_code ON test_records (calibration_code)",
    ]
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
    print("ZENPSA DB: classification migration verified", flush=True)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
