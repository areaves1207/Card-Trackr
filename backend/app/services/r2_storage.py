"""
Cloudflare R2 upload service (S3-compatible).

R2 uses the same API as Amazon S3, so we use the boto3 library with a custom endpoint URL.
This means if you ever want to switch to real S3, you only change the endpoint and credentials.
"""

import uuid

import boto3
from botocore.config import Config

from app.config import settings

_client = None


def get_r2_client():
    global _client
    if _client is None and settings.r2_account_id:
        _client = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
    return _client


async def upload_file(file_bytes: bytes, filename: str, content_type: str) -> str | None:
    """
    Upload bytes to R2 and return the public URL.
    Returns None if R2 is not configured (dev mode — files aren't persisted).
    """
    client = get_r2_client()
    if not client:
        return None  # R2 not configured — skip upload in local dev

    key = f"uploads/{uuid.uuid4()}/{filename}"
    client.put_object(
        Bucket=settings.r2_bucket_name,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )

    base = settings.r2_public_url.rstrip("/") if settings.r2_public_url else ""
    return f"{base}/{key}" if base else None
