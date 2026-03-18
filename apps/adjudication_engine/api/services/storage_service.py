import uuid
from datetime import datetime, timezone
from functools import lru_cache
import boto3
from botocore.client import Config
from api.core.config import settings


def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
        region_name="auto",
    )


def generate_upload_key(filename: str, user_id: str) -> str:
    now = datetime.now(timezone.utc)
    uid = str(uuid.uuid4())[:8]
    return f"claims/{now.year}/{now.month:02d}/{user_id}/{uid}/{filename}"


def generate_presigned_upload_url(key: str, content_type: str) -> str:
    client = get_r2_client()
    return client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.R2_BUCKET_NAME,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=600,
    )


def generate_presigned_download_url(key: str) -> str:
    client = get_r2_client()
    return client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.R2_BUCKET_NAME,
            "Key":    key,
        },
        ExpiresIn=900,
    )


def upload_bytes(key: str, data: bytes, content_type: str = "application/pdf") -> None:
    client = get_r2_client()
    client.put_object(
        Bucket=settings.R2_BUCKET_NAME,
        Key=key,
        Body=data,
        ContentType=content_type,
    )


def delete_document(key: str) -> None:
    client = get_r2_client()
    client.delete_object(
        Bucket=settings.R2_BUCKET_NAME,
        Key=key,
    )
