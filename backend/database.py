import os
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def _database_url() -> str:
    value = os.getenv("DATABASE_URL", "sqlite:///./zenpsa_local.db")

    if value.startswith("postgres://"):
        return value.replace(
            "postgres://",
            "postgresql+psycopg://",
            1,
        )

    if value.startswith("postgresql://"):
        return value.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )

    return value


DATABASE_URL = _database_url()

CONNECT_ARGS = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args=CONNECT_ARGS,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def create_database_tables() -> None:
    """Register all ORM models, create missing tables and run migrations."""

    # These imports must occur before Base.metadata.create_all().
    # Importing the models registers their tables in SQLAlchemy metadata.
    from record_models import TestRecord
    from qms_models import (
        QmsLot,
        QmsLotRecordType,
        QmsLotRelationship,
        QmsProduct,
        QmsQcRecord,
    )

    # Silence linters while keeping the model-registration imports explicit.
    _ = (
        TestRecord,
        QmsLot,
        QmsLotRecordType,
        QmsLotRelationship,
        QmsProduct,
        QmsQcRecord,
    )

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        from qms_service import seed_qms_master_data

        seed_qms_master_data(session)

    if not DATABASE_URL.startswith("sqlite"):
        migrate_record_classification_columns()
        migrate_qms_qc_columns()


def migrate_record_classification_columns() -> None:
    """Apply idempotent PostgreSQL migrations for test_records."""

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
        "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS captured_date DATE",
        "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS recruitment_center VARCHAR(120)",
        "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS device_model VARCHAR(160)",
        "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS device_platform VARCHAR(80)",
        "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS device_platform_version VARCHAR(80)",
        "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS device_browser VARCHAR(200)",
        "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS device_mobile BOOLEAN",
        "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS device_user_agent TEXT",
        "UPDATE test_records SET captured_date = captured_at::date WHERE captured_date IS NULL",
        "CREATE INDEX IF NOT EXISTS ix_test_records_captured_date ON test_records (captured_date)",
        "CREATE INDEX IF NOT EXISTS ix_test_records_recruitment_center ON test_records (recruitment_center)",
        "CREATE INDEX IF NOT EXISTS ix_test_records_record_purpose ON test_records (record_purpose)",
        "CREATE INDEX IF NOT EXISTS ix_test_records_calibration_code ON test_records (calibration_code)",
    ]

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

    print(
        "ZENPSA DB: classification migration verified",
        flush=True,
    )


def migrate_qms_qc_columns() -> None:
    """Apply idempotent PostgreSQL migrations for QMS QC records."""

    statements = [
        "ALTER TABLE qms_qc_records ADD COLUMN IF NOT EXISTS analysis_data_json TEXT",
        "CREATE INDEX IF NOT EXISTS ix_qms_qc_records_lot_id ON qms_qc_records (lot_id)",
        "CREATE INDEX IF NOT EXISTS ix_qms_qc_records_qc_type ON qms_qc_records (qc_type)",
        "CREATE INDEX IF NOT EXISTS ix_qms_qc_records_captured_at ON qms_qc_records (captured_at)",
        "CREATE INDEX IF NOT EXISTS ix_qms_qc_records_lot_date ON qms_qc_records (lot_id, captured_at)",
    ]

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

    print(
        "ZENPSA DB: QMS QC migration verified",
        flush=True,
    )


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
