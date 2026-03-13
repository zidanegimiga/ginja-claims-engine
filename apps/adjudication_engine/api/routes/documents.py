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
    content_type: str
    document_index: Literal[0, 1] = 0  # 0 = primary, 1 = secondary


class PresignedUploadResponse(BaseModel):
    upload_url: str
    document_key: str
    document_name: str
    document_index: int


class DocumentUrlResponse(BaseModel):
    url: str
    expires_in: int = 900  # seconds


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
    claim_id:       str,
    document_index: int = Query(default=0, ge=0, le=1),
    current_user:   dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Generates a temporary presigned download URL for a document
    attached to a claim. document_index=0 is primary, 1 is secondary.
    """
    claim = await db.claims.find_one({"claim_id": claim_id})
    if not claim:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Claim not found")

    source    = claim.get("source", {})
    documents = source.get("documents", [])

    if document_index >= len(documents):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"No document at index {document_index} for this claim"
        )

    key = documents[document_index]["document_key"]
    url = generate_presigned_download_url(key)
    return DocumentUrlResponse(url=url)
