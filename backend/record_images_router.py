import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from database import get_db
from record_models import TestRecord
from r2_storage import (R2ConfigurationError, configuration_status, create_download_url,
                        delete_object, upload_jpeg)

router = APIRouter(prefix="/records", tags=["record-images"])
MAX_IMAGE_BYTES = 15 * 1024 * 1024


def _record(db: Session, record_id: uuid.UUID) -> TestRecord:
    record = db.get(TestRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return record

@router.get("/images/health")
def image_storage_health():
    return configuration_status()

@router.post("/{record_id}/image", status_code=status.HTTP_201_CREATED)
async def upload_record_image(record_id: uuid.UUID, image: UploadFile = File(...), db: Session = Depends(get_db)):
    record = _record(db, record_id)
    if image.content_type not in {"image/jpeg", "image/jpg"}:
        raise HTTPException(status_code=415, detail="Only JPEG images are accepted")
    data = await image.read(MAX_IMAGE_BYTES + 1)
    if not data:
        raise HTTPException(status_code=422, detail="Empty image")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds 15 MB")
    if not (data.startswith(b"\xff\xd8") and data.endswith(b"\xff\xd9")):
        raise HTTPException(status_code=422, detail="Invalid JPEG signature")
    expected = f"{record.base_filename}.jpg"
    record.image_storage_status = "PENDING"
    record.image_upload_error = None
    db.commit()
    try:
        domain = "clinical"
        session_id = None
        if record.record_purpose == "research": domain = "research"
        elif record.record_purpose == "calibration":
            domain = f"calibrations/{record.calibration_analyte or 'unknown'}"
            session_id = record.calibration_code
        stored = upload_jpeg(str(record.id), expected, data, domain=domain, session_id=session_id)
        old_key = record.image_object_key
        record.image_storage_status = "UPLOADED"
        record.image_object_key = stored.object_key
        record.image_filename = stored.filename
        record.image_content_type = stored.content_type
        record.image_size_bytes = stored.size_bytes
        record.image_sha256 = stored.sha256
        record.image_uploaded_at = stored.uploaded_at
        db.commit(); db.refresh(record)
        if old_key and old_key != stored.object_key:
            try: delete_object(old_key)
            except Exception: pass
        return {"record_id": record.id, "status": record.image_storage_status,
                "filename": record.image_filename, "size_bytes": record.image_size_bytes,
                "sha256": record.image_sha256, "uploaded_at": record.image_uploaded_at}
    except Exception as exc:
        db.rollback()
        record = _record(db, record_id)
        record.image_storage_status = "FAILED"
        record.image_upload_error = str(exc)[:1000]
        db.commit()
        code = 503 if isinstance(exc, R2ConfigurationError) else 502
        raise HTTPException(status_code=code, detail=f"R2 upload failed: {exc}") from exc

@router.get("/{record_id}/image-url")
def record_image_url(record_id: uuid.UUID, db: Session = Depends(get_db)):
    record = _record(db, record_id)
    if record.image_storage_status != "UPLOADED" or not record.image_object_key:
        raise HTTPException(status_code=404, detail="Image not available")
    try:
        url, expiry = create_download_url(record.image_object_key)
        return {"record_id": record.id, "url": url, "expires_in_seconds": expiry,
                "filename": record.image_filename, "sha256": record.image_sha256}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to create image URL: {exc}") from exc

@router.delete("/{record_id}/image", status_code=status.HTTP_204_NO_CONTENT)
def delete_record_image(record_id: uuid.UUID, db: Session = Depends(get_db)):
    record = _record(db, record_id)
    if record.image_object_key:
        try: delete_object(record.image_object_key)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"R2 delete failed: {exc}") from exc
    record.image_storage_status = "DELETED"
    record.image_object_key = None; record.image_filename = None
    record.image_content_type = None; record.image_size_bytes = None
    record.image_sha256 = None; record.image_uploaded_at = None
    record.image_upload_error = None
    db.commit()
