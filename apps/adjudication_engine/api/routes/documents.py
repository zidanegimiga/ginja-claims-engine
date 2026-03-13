from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional

from api.routes.auth import get_current_user
from api.services.storage_service import (
    generate_upload_key,
    generate_presigned_upload_url,
    generate_presigned_download_url,
)
from db.mongo import get_db

router = APIRouter(prefix="/documents", tags=["Documents"])


class PresignedUploadRequest(BaseModel):
    filename: str
    content_type: str  # "application/pdf", "text/csv"


class PresignedUploadResponse(BaseModel):
    upload_url: str
    document_key: str
    document_name: str


class DocumentUrlResponse(BaseModel):
    url:          str
    expires_in:   int = 900  # seconds


# Generate presigned upload URL

@router.post("/upload-url", response_model=PresignedUploadResponse)
async def get_upload_url(
    body:         PresignedUploadRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Returns a presigned URL for direct browser-to-R2 upload.
    The frontend PUTs the file to this URL, then includes
    document_key in the adjudication request.
    """
    allowed_types = {
        "application/pdf",
        "text/csv",
        "application/json",
        "image/jpeg",
        "image/png",
    }
    if body.content_type not in allowed_types:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unsupported file type: {body.content_type}"
        )

    key        = generate_upload_key(body.filename, current_user["_id"])
    upload_url = generate_presigned_upload_url(key, body.content_type)

    return PresignedUploadResponse(
        upload_url=upload_url,
        document_key=key,
        document_name=body.filename,
    )


# Get document download URL (role-gated)

@router.get("/view/{claim_id}", response_model=DocumentUrlResponse)
async def get_document_url(
    claim_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Generates a temporary presigned download URL for the document
    attached to a claim. Viewers and above can access.
    The URL expires in 15 minutes and is never stored.
    """
    claim = await db.claims.find_one({"claim_id": claim_id})
    if not claim:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Claim not found")

    source = claim.get("source")
    if not source or not source.get("document_key"):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No document attached to this claim"
        )

    url = generate_presigned_download_url(source["document_key"])
    return DocumentUrlResponse(url=url)