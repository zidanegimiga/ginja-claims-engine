import io
import json
import pandas as pd
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Request, Depends
from api.auth_keys import validate_api_key, get_client_ip
from fastapi.responses import JSONResponse
from api.schemas import ClaimRequest, AdjudicationResponse, BatchClaimRequest
from engine.adjudicator import adjudicate
from monitoring.logger import log_adjudication
from db.mongo import save_adjudication_result, get_adjudication_result, list_adjudication_results
from fastapi import WebSocket, WebSocketDisconnect, Query as WsQuery
import asyncio
import uuid
from api.services.extraction_service import extract_claim_from_pdf
from pydantic import BaseModel
from api.middleware import verify_api_key
from api.services.storage_service import (
    get_r2_client,
    generate_upload_key,
    generate_presigned_download_url,
)


router = APIRouter()


class ExtractRequest(BaseModel):
    document_key: str


@router.post("/extract")
async def extract_claim(
    body: ExtractRequest,
    api_key: str = Depends(verify_api_key),
):
    """Download PDF from R2 and extract structured claim data."""
    import boto3
    from botocore.exceptions import ClientError
    from core.config import settings

    # Download from R2
    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",
        )
        obj = s3.get_object(Bucket=settings.r2_bucket_name, Key=body.document_key)
        pdf_bytes = obj["Body"].read()
    except ClientError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Document not found: {body.document_key}"
        )

    # Extract
    result = extract_claim_from_pdf(pdf_bytes)
    return result


router.websocket("/ws/adjudicate")
async def ws_adjudicate(
    websocket: WebSocket,
    api_key: str = WsQuery(default=None),
):
    # Validate API key before accepting
    from api.auth_keys import validate_api_key
    try:
        validate_api_key(api_key, "write", websocket.client.host)
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            job_id = data.get("job_id", str(uuid.uuid4()))

            # Acknowledge receipt
            await websocket.send_json({"job_id": job_id, "status": "processing"})

            try:
                # Run adjudication in thread pool — keeps the event loop free
                result = await asyncio.get_event_loop().run_in_executor(
                    None, adjudicate, data
                )
                await save_adjudication_result(result)
                log_adjudication(result)

                await websocket.send_json({
                    "job_id": job_id,
                    "status": "done",
                    "result": result,
                })
            except Exception as e:
                await websocket.send_json({
                    "job_id": job_id,
                    "status": "error",
                    "error":  str(e),
                })

    except WebSocketDisconnect:
        pass

def require_write(request: Request) -> dict:
    """
    FastAPI dependency for write scope authentication.
    When used with Depends(), FastAPI runs this before
    any request body parsing or schema validation.
    This ensures unauthenticated requests are rejected
    immediately without processing the payload.
    """
    key = request.headers.get("X-API-Key")
    ip  = get_client_ip(request)
    return validate_api_key(key, "write", ip)


def require_read(request: Request) -> dict:
    key = request.headers.get("X-API-Key")
    ip  = get_client_ip(request)
    return validate_api_key(key, "read", ip)

@router.post(
    "/adjudicate",
    response_model=AdjudicationResponse,
    tags=["Claims"],
    summary="Adjudicate a single claim",
    description="""
    Submit a single healthcare claim for adjudication.
    Returns a decision (Pass / Flag / Fail), risk score,
    confidence, and plain-English explanation.
    """
)
async def adjudicate_claim(claim: ClaimRequest, request: Request, auth: dict = Depends(require_write)):
    """
    Single claim adjudication endpoint.
    Accepts a JSON payload, runs it through all three
    adjudication stages, and returns the result.
    """
    try:
        raw_claim = claim.model_dump()
        result = adjudicate(raw_claim)

        await save_adjudication_result(result)

        log_adjudication(result)

        return AdjudicationResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/adjudicate/batch",
    tags=["Claims"],
    summary="Adjudicate multiple claims from JSON",
    description="Submit an array of claims and receive decisions for all of them."
)
async def adjudicate_batch(batch: BatchClaimRequest, request: Request, auth:    dict = Depends(require_write)):
    """
    Batch adjudication from a JSON array.
    Processes each claim sequentially and returns all results.
    """

    results = []
    errors = []

    for claim in batch.claims:
        try:
            raw_claim = claim.model_dump()
            result = adjudicate(raw_claim)
            await save_adjudication_result(result)
            log_adjudication(result)
            results.append(result)
        except Exception as e:
            errors.append({
                "claim_id": claim.claim_id,
                "error": str(e)
            })

    return {
        "total": len(batch.claims),
        "processed": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors,
    }


@router.post(
    "/adjudicate/upload/csv",
    tags=["Claims"],
    summary="Upload a CSV file of claims",
    description="Upload a CSV file. Each row is adjudicated and results returned."
)
async def adjudicate_csv(file: UploadFile = File(...), request: Request = None, auth: dict = Depends(require_write)):
    """
    CSV file upload endpoint.
    Reads each row as a claim, adjudicates it,
    and returns all results.
    """
    require_write(request)

    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are accepted at this endpoint"
        )

    try:
        contents  = await file.read()
        dataframe = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    results = []
    errors  = []

    for _, row in dataframe.iterrows():
        try:
            raw_claim = row.to_dict()
            # Convert NaN values to None
            raw_claim = {
                k: (None if pd.isna(v) else v)
                for k, v in raw_claim.items()
            }
            result = adjudicate(raw_claim)
            await save_adjudication_result(result)
            log_adjudication(result)
            results.append(result)
        except Exception as e:
            errors.append({
                "row": int(row.get("claim_id", "unknown")),
                "error": str(e)
            })

    return {
        "filename": file.filename,
        "total": len(dataframe),
        "processed": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors,
    }

@router.get(
    "/claims/{claim_id}",
    tags=["Claims"],
    summary="Retrieve a previously adjudicated claim"
)
async def get_claim(
    claim_id: str,
    request: Request,
    auth: dict = Depends(require_read),
):
    """
    Retrieves the full adjudication record for a claim
    from MongoDB by claim ID.
    """

    result = await get_adjudication_result(claim_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    return result


@router.get(
    "/claims",
    tags    = ["Claims"],
    summary = "List adjudicated claims with optional filters",
)
async def list_claims(
    request:  Request,
    decision: str = Query(default=None),
    limit: int = Query(default=20, ge=1, le=1000),
    skip: int = Query(default=0, ge=0),
    auth: dict = Depends(require_read),
):
    """
    Returns a paginated list of adjudicated claims.
    Optionally filter by decision type.
    """

    results = await list_adjudication_results(
        decision=decision, limit=limit, skip=skip
    )
    return {"total": len(results), "skip": skip, "limit": limit, "results": results}


@router.post(
    "/adjudicate/upload/pdf",
    tags=["Claims"],
    summary="Upload a PDF claim form for extraction and adjudication",
    description="""
    Upload a PDF claim form or invoice.
    The system extracts structured data using the configured
    vision provider (Gemini, Ollama, Qwen, or Tesseract),
    validates the extracted fields, then adjudicates the claim.

    Optionally specify which vision provider and model to use
    via query parameters.
    """
)
async def adjudicate_pdf(
    request:  Request,
    auth: dict = Depends(require_write),
    file: UploadFile = File(...),
    provider: str = Query(
        default=None,
        description="Vision provider: gemini, ollama, qwen, tesseract"
    ),
    model: str = Query(
        default=None,
        description="Model name override e.g. qwen2-vl, llava, gemini-1.5-pro"
    ),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted at this endpoint"
        )

    import tempfile
    import os
    from extraction.factory import get_vision_provider
    from extraction.validator import validate_extracted_claim

    # Save uploaded PDF to a temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        # Get the appropriate vision provider
        vision_provider = get_vision_provider(provider=provider, model=model)

        # Extract structured data from the PDF
        extracted = vision_provider.extract(tmp_path)

        # Validate extracted fields
        validated = validate_extracted_claim(extracted)

        if not validated["is_valid"]:
            return JSONResponse(
                status_code=422,
                content={
                    "error": "PDF extraction incomplete",
                    "validation_errors": validated["validation_errors"],
                    "extracted_data": validated,
                    "suggestion": (
                        "Try a different vision provider with the ?provider= "
                        "query parameter. Options: gemini, ollama, qwen, tesseract"
                    )
                }
            )

        # Adjudicate the extracted claim
        result = adjudicate(validated)
        result["extraction_metadata"] = {
            "provider": validated.get("provider_name"),
            "confidence": validated.get("confidence"),
            "warnings": validated.get("extraction_warnings", []),
        }

        await save_adjudication_result(result)
        log_adjudication(result)

        return result

    finally:
        # Clean up temp file
        os.unlink(tmp_path)


@router.post(
    "/claims/upload",
    tags=["Claims"],
    summary="Upload a PDF to R2 storage",
)
async def upload_document(
    request: Request,
    auth: dict = Depends(require_write),
    file: UploadFile = File(...),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    contents = await file.read()
    user_id = auth.get("key_id", "unknown")
    document_key = generate_upload_key(file.filename, user_id)

    try:
        client = get_r2_client()
        client.put_object(
            Bucket=os.environ["R2_BUCKET_NAME"],
            Key=document_key,
            Body=contents,
            ContentType="application/pdf",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

    return {
        "key": document_key,
        "filename": file.filename,
        "size": len(contents),
    }


@router.get(
    "/claims/document-url",
    tags=["Claims"],
    summary="Get a presigned URL for a stored document",
)
async def get_document_url(
    key: str = Query(..., description="R2 object key"),
    request: Request = None,
    auth: dict = Depends(require_read),
):
    try:
        url = generate_presigned_download_url(key)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Document not found: {key}")

    return {"url": url}
