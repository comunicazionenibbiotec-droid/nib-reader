import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from database import get_db
from record_models import TestRecord
from record_schemas import (
    RecordCreate,
    RecordDetail,
    RecordPatch,
    RecordSummary,
)
from record_service import (
    create_or_update_record,
    patch_record,
)


router = APIRouter(
    prefix="/records",
    tags=["records"],
)


@router.post(
    "",
    response_model=RecordDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_record(
    payload: RecordCreate,
    db: Session = Depends(get_db),
):
    return create_or_update_record(
        db,
        payload,
    )


@router.get(
    "",
    response_model=list[RecordSummary],
)
def list_records(
    sample_code: str | None = None,
    clinical_pathway: str | None = None,
    diagnosis: str | None = None,
    record_purpose: str | None = None,
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: Session = Depends(get_db),
):
    query = select(TestRecord)

    if sample_code:
        query = query.where(
            TestRecord.sample_code.ilike(
                f"%{sample_code}%"
            )
        )

    if clinical_pathway:
        query = query.where(
            TestRecord.clinical_pathway
            == clinical_pathway
        )

    if diagnosis:
        query = query.where(
            TestRecord.diagnosis
            == diagnosis
        )

    if record_purpose:
        query = query.where(
            TestRecord.record_purpose
            == record_purpose
        )

    query = (
        query
        .order_by(
            TestRecord.captured_at.desc()
        )
        .offset(offset)
        .limit(limit)
    )

    return list(
        db.scalars(query)
    )


# IMPORTANTE:
# Questa rotta deve rimanere prima di /{record_id}.
@router.get("/health")
def records_health(
    db: Session = Depends(get_db),
):
    database_check = db.execute(
        text("SELECT 1")
    ).scalar_one()

    table_exists = db.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'test_records'
            )
            """
        )
    ).scalar_one()

    current_database = db.execute(
        text(
            "SELECT current_database()"
        )
    ).scalar_one()

    current_user = db.execute(
        text(
            "SELECT current_user"
        )
    ).scalar_one()

    classification_columns = db.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'test_records'
              AND column_name IN (
                  'record_purpose',
                  'study_code',
                  'calibration_code',
                  'calibration_analyte',
                  'nominal_concentration_ug_ml',
                  'replicate_number'
              )
            ORDER BY column_name
            """
        )
    ).scalars().all()

    required_columns = {
        "record_purpose",
        "study_code",
        "calibration_code",
        "calibration_analyte",
        "nominal_concentration_ug_ml",
        "replicate_number",
    }

    available_columns = set(
        classification_columns
    )

    return {
        "database_connected": (
            database_check == 1
        ),
        "test_records_table_exists": (
            bool(table_exists)
        ),
        "classification_columns_ready": (
            required_columns.issubset(
                available_columns
            )
        ),
        "classification_columns": sorted(
            available_columns
        ),
        "database": current_database,
        "user": current_user,
    }


@router.get(
    "/{record_id}",
    response_model=RecordDetail,
)
def get_record(
    record_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    record = db.get(
        TestRecord,
      