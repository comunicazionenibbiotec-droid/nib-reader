import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timezone

import boto3
from botocore.client import Config


class R2ConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredImage:
    object_key: str
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    uploaded_at: datetime


def _env(name: str, required: bool = True) -> str | None:
    value = os.getenv(name)
    if required and not value:
        raise R2ConfigurationError(f"Missing environment variable: {name}")
    return value


def enabled() -> bool:
    return os.getenv("R2_ENABLED", "false").lower() in {"1", "true", "yes", "on"}


def bucket_name() -> str:
    return str(_env("R2_BUCKET_NAME"))


def image_prefix() -> str:
    return os.getenv("R2_IMAGE_PREFIX", "clinical-images").strip("/")


def presigned_expiry() -> int:
    try:
        return max(60, min(3600, int(os.getenv("R2_PRESIGNED_URL_EXPIRY_SECONDS", "600"))))
    except ValueError:
        return 600


def client():
    if not enabled():
        raise R2ConfigurationError("R2 storage is disabled")
    return boto3.client(
        "s3",
        endpoint_url=_env("R2_ENDPOINT_URL"),
        aws_access_key_id=_env("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=_env("R2_SECRET_ACCESS_KEY"),
        region_name=os.getenv("R2_REGION", "auto"),
        config=Config(signature_version="s3v4"),
    )


def build_object_key(record_id: str, filename: str) -> str:
    safe = "".join(c for c in filename if c.isalnum() or c in "._-")
    return f"{image_prefix()}/{record_id}/{safe}"


def upload_jpeg(record_id: str, filename: str, data: bytes) -> StoredImage:
    digest = hashlib.sha256(data).hexdigest()
    key = build_object_key(record_id, filename)
    client().put_object(
        Bucket=bucket_name(), Key=key, Body=data,
        ContentType="image/jpeg",
        Metadata={"sha256": digest, "record-id": record_id},
    )
    return StoredImage(key, filename, "image/jpeg", len(data), digest, datetime.now(timezone.utc))


def delete_object(object_key: str) -> None:
    client().delete_object(Bucket=bucket_name(), Key=object_key)


def create_download_url(object_key: str) -> tuple[str, int]:
    expiry = presigned_expiry()
    url = client().generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name(), "Key": object_key},
        ExpiresIn=expiry,
    )
    return url, expiry


def configuration_status() -> dict:
    names = ["R2_BUCKET_NAME", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_ENDPOINT_URL"]
    missing = [name for name in names if not os.getenv(name)]
    return {"enabled": enabled(), "configured": enabled() and not missing, "missing": missing,
            "bucket": os.getenv("R2_BUCKET_NAME"), "prefix": image_prefix(),
            "presigned_url_expiry_seconds": presigned_expiry()}
