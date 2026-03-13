import os
import boto3
from botocore.client import Config
from datetime import datetime, timezone
import uuid


def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def generate_upload_key(filename: str, user_id: str) -> str:
    """
    Generates a structured R2 object key.
    Format: claims/{year}/{month}/{user_id}/{uuid}/{filename}
    """
    now = datetime.now(timezone.utc)
    uid = str(uuid.uuid4())[:8]
    return f"claims/{now.year}/{now.month:02d}/{user_id}/{uid}/{filename}"


def generate_presigned_upload_url(key: str, content_type: str) -> str:
    """
    Generates a presigned URL for direct browser-to-R2 upload.
    Expires in 10 minutes.
    """
    client = get_r2_client()
    return client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": os.environ["R2_BUCKET_NAME"],
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=600,  # 10 minutes
    )


def generate_presigned_download_url(key: str) -> str:
    """
    Generates a temporary presigned URL for viewing/downloading a document.
    Expires in 15 minutes. Generated on demand — never stored.
    """
    client = get_r2_client()
    return client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": os.environ["R2_BUCKET_NAME"],
            "Key": key,
        },
        ExpiresIn=900,  # 15 minutes
    )


def delete_document(key: str) -> None:
    client = get_r2_client()
    client.delete_object(
        Bucket=os.environ["R2_BUCKET_NAME"],
        Key=key,
    )