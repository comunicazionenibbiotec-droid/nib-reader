from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from record_models import TestRecord
from record_schemas import RecordCreate, RecordPatch


def _first_defined(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None

def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _integer(value: Any) -> int | None:
    number = _number(value)
    return int(number) if number is not None else None


def _date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _iso_date(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _captured_at(record_info: dict[str, Any]) -> datetime:
    value = record_info.get("captured_at_utc") or record_info.get(
        "captured_at_local"
    )
    if not value:
        return datetime.now(timezone.utc)

    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def create_or_update_record(
    session: Session,
    payload: RecordCreate,
) -> TestRecord:
    raw = payload.model_dump(mode="json", exclude_none=False)
    info = payload.record
    subject = payload.subject
    classification = payload.classification or {}
    analysis = payload.analysis
    backend = analysis.get("backend", analysis)
    analytical = backend.get("analytical_reading") or {}
    window_a = analytical.get("A") or {}
    window_c = analytical.get("C") or {}
    absolute = window_a.get("absolute_measurement") or {}
    ratios = window_c.get("ratios") or {}
    manual = payload.manual_data or {}
    clinical = manual.get("clinical") or {}
    upsa = manual.get("upsa") or {}
    uzinc = manual.get("uzinc") or {}

    base_filename = str(info.get("base_filename") or "").strip()
    sample_code = str(subject.get("sample_code") or "").strip()

    if not base_filename or not sample_code:
        raise HTTPException(
            status_code=422,
            detail="base_filename and sample_code are required",
        )

    existing = session.scalar(
        select(TestRecord).where(
            TestRecord.base_filename == base_filename
        )
    )

    record = existing or TestRecord(
        base_filename=base_filename,
        sample_code=sample_code,
        captured_at=_captured_at(info),
        raw_record=raw,
    )

    record.sample_code = sample_code
    record.progressive_number = _integer(info.get("progressive_number"))
    record.captured_at = _captured_at(info)
    record.clinical_pathway = subject.get("clinical_pathway")
    record.record_purpose = classification.get("record_purpose", "unclassified")
    record.study_code = classification.get("study_code")
    record.calibration_code = classification.get("calibration_code")
    record.calibration_analyte = classification.get("calibration_analyte")
    record.nominal_concentration_ug_ml = _number(
        classification.get("nominal_concentration_ug_ml")
    )
    record.replicate_number = _integer(classification.get("replicate_number"))
    record.urine_collection_volume_ml = _number(
        _first_defined(
            subject.get("urine_collection_volume_ml"),
            subject.get("urine_volume_ml"),
        )
    )
    record.optical_zinc_score_0_4 = _integer(
        _first_defined(
            subject.get("optical_zinc_score_0_4"),
            subject.get("visual_zinc_score_0_4"),
        )
    )
    record.optical_psa_score_0_4 = _integer(
        _first_defined(
            subject.get("optical_psa_score_0_4"),
            subject.get("visual_psa_score_0_4"),
        )
    )
    record.zinc_red_excess = _number(absolute.get("red_excess"))
    record.psa_area_t_c_ratio = _number(
        ratios.get("peak_area_T_over_C")
    )
    record.test_state = (
        backend.get("test_state") or window_c.get("test_state")
    )
    record.test_valid = bool(backend.get("test_valid", False))
    record.lot_id = analytical.get("lot_id")

    record.age = _integer(clinical.get("age", subject.get("age")))
    record.serum_psa_ng_ml = _number(
        clinical.get(
            "serum_psa_ng_ml",
            subject.get("serum_psa_ng_ml"),
        )
    )
    record.dre_result = clinical.get(
        "dre_result",
        subject.get("dre_result"),
    )
    record.pirads = _integer(
        clinical.get("pirads", subject.get("pirads"))
    )
    record.prostate_volume_ml = _number(
        clinical.get(
            "prostate_volume_ml",
            subject.get("prostate_volume_ml"),
        )
    )
    record.gleason_score = clinical.get(
        "gleason_score",
        subject.get("gleason_score"),
    )
    record.diagnosis = clinical.get("diagnosis")
    record.raw_record = raw

    if upsa:
        _apply_instrument(record, "upsa", upsa)
    if uzinc:
        _apply_instrument(record, "uzinc", uzinc)

    if not existing:
        session.add(record)

    session.commit()
    session.refresh(record)
    return record


def _apply_instrument(
    record: TestRecord,
    prefix: str,
    data: dict[str, Any],
) -> None:
    setattr(
        record,
        f"{prefix}_instrumental_ug_ml",
        _number(data.get("value_ug_ml")),
    )
    setattr(
        record,
        f"{prefix}_execution_date",
        _date(data.get("execution_date")),
    )
    setattr(
        record,
        f"{prefix}_rapid_frozen",
        bool(data.get("rapid_test_frozen", False)),
    )
    setattr(
        record,
        f"{prefix}_rapid_frozen_date",
        _date(data.get("rapid_test_frozen_date")),
    )
    setattr(
        record,
        f"{prefix}_instrumental_frozen",
        bool(data.get("instrumental_frozen", False)),
    )
    setattr(
        record,
        f"{prefix}_instrumental_frozen_date",
        _date(data.get("instrumental_frozen_date")),
    )


def patch_record(
    session: Session,
    record: TestRecord,
    payload: RecordPatch,
) -> TestRecord:
    if payload.subject is not None:
        subject_data = payload.subject.model_dump(exclude_unset=True)
        subject_columns = {
            "sample_code": "sample_code",
            "urine_collection_volume_ml": "urine_collection_volume_ml",
            "clinical_pathway": "clinical_pathway",
            "optical_zinc_score_0_4": "optical_zinc_score_0_4",
            "optical_psa_score_0_4": "optical_psa_score_0_4",
        }
        for source_name, column_name in subject_columns.items():
            if source_name in subject_data:
                setattr(record, column_name, subject_data[source_name])

    if payload.classification is not None:
        classification_data = payload.classification.model_dump(exclude_unset=True)
        classification_columns = {
            "record_purpose": "record_purpose",
            "study_code": "study_code",
            "calibration_code": "calibration_code",
            "calibration_analyte": "calibration_analyte",
            "nominal_concentration_ug_ml": "nominal_concentration_ug_ml",
            "replicate_number": "replicate_number",
        }
        for source_name, column_name in classification_columns.items():
            if source_name in classification_data:
                setattr(record, column_name, classification_data[source_name])
        if "notes" in classification_data:
            record.notes = classification_data["notes"]

    if payload.clinical is not None:
        clinical_data = payload.clinical.model_dump(exclude_unset=True)
        for name, value in clinical_data.items():
            setattr(record, name, value)

    if payload.upsa is not None:
        _patch_instrument(
            record,
            "upsa",
            payload.upsa.model_dump(),
        )

    if payload.uzinc is not None:
        _patch_instrument(
            record,
            "uzinc",
            payload.uzinc.model_dump(),
        )

    if "notes" in payload.model_fields_set:
        record.notes = payload.notes

    # Build a new JSON-serializable object. Date values must be ISO strings,
    # not Python date objects, before they are written to JSON/JSONB.
    raw_record = dict(record.raw_record or {})
    raw_subject = dict(raw_record.get("subject") or {})
    raw_subject.update({
        "sample_code": record.sample_code,
        "urine_collection_volume_ml": record.urine_collection_volume_ml,
        "clinical_pathway": record.clinical_pathway,
        "optical_zinc_score_0_4": record.optical_zinc_score_0_4,
        "optical_psa_score_0_4": record.optical_psa_score_0_4,
    })
    raw_record["subject"] = raw_subject
    raw_classification = dict(raw_record.get("classification") or {})
    raw_classification.update({
        "record_purpose": record.record_purpose,
        "study_code": record.study_code,
        "calibration_code": record.calibration_code,
        "calibration_analyte": record.calibration_analyte,
        "nominal_concentration_ug_ml": record.nominal_concentration_ug_ml,
        "replicate_number": record.replicate_number,
        "notes": record.notes,
    })
    raw_record["classification"] = raw_classification
    manual = dict(raw_record.get("manual_data") or {})

    manual["clinical"] = {
        "age": record.age,
        "serum_psa_ng_ml": record.serum_psa_ng_ml,
        "dre_result": record.dre_result,
        "pirads": record.pirads,
        "prostate_volume_ml": record.prostate_volume_ml,
        "gleason_score": record.gleason_score,
        "diagnosis": record.diagnosis,
    }
    manual["upsa"] = _instrument_json(record, "upsa")
    manual["uzinc"] = _instrument_json(record, "uzinc")
    manual["updated_at"] = datetime.now(timezone.utc).isoformat()

    raw_record["manual_data"] = manual
    record.raw_record = raw_record

    try:
        session.commit()
        session.refresh(record)
        return record
    except Exception:
        session.rollback()
        raise


def _patch_instrument(
    record: TestRecord,
    prefix: str,
    data: dict[str, Any],
) -> None:
    setattr(
        record,
        f"{prefix}_instrumental_ug_ml",
        data.get("value_ug_ml"),
    )
    setattr(
        record,
        f"{prefix}_execution_date",
        data.get("execution_date"),
    )
    setattr(
        record,
        f"{prefix}_rapid_frozen",
        data.get("rapid_test_frozen", False),
    )
    setattr(
        record,
        f"{prefix}_rapid_frozen_date",
        data.get("rapid_test_frozen_date"),
    )
    setattr(
        record,
        f"{prefix}_instrumental_frozen",
        data.get("instrumental_frozen", False),
    )
    setattr(
        record,
        f"{prefix}_instrumental_frozen_date",
        data.get("instrumental_frozen_date"),
    )


def _instrument_json(
    record: TestRecord,
    prefix: str,
) -> dict[str, Any]:
    return {
        "value_ug_ml": getattr(
            record,
            f"{prefix}_instrumental_ug_ml",
        ),
        "execution_date": _iso_date(
            getattr(record, f"{prefix}_execution_date")
        ),
        "rapid_test_frozen": getattr(
            record,
            f"{prefix}_rapid_frozen",
        ),
        "rapid_test_frozen_date": _iso_date(
            getattr(record, f"{prefix}_rapid_frozen_date")
        ),
        "instrumental_frozen": getattr(
            record,
            f"{prefix}_instrumental_frozen",
        ),
        "instrumental_frozen_date": _iso_date(
            getattr(record, f"{prefix}_instrumental_frozen_date")
        ),
    }
