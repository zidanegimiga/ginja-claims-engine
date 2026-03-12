import io
import json
import pandas as pd
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import JSONResponse
from api.schemas import ClaimRequest, AdjudicationResponse, BatchClaimRequest
from engine.adjudicator import adjudicate
from monitoring.logger import log_adjudication
from db.mongo import save_adjudication_result

router = APIRouter()


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
async def adjudicate_claim(claim: ClaimRequest):
    """
    Single claim adjudication endpoint.
    Accepts a JSON payload, runs it through all three
    adjudication stages, and returns the result.
    """
    try:
        raw_claim = claim.model_dump()
        result    = adjudicate(raw_claim)

        # Save to MongoDB asynchronously
        await save_adjudication_result(result)

        # Log for monitoring
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
async def adjudicate_batch(batch: BatchClaimRequest):
    """
    Batch adjudication from a JSON array.
    Processes each claim sequentially and returns all results.
    """
    results = []
    errors  = []

    for claim in batch.claims:
        try:
            raw_claim = claim.model_dump()
            result    = adjudicate(raw_claim)
            await save_adjudication_result(result)
            log_adjudication(result)
            results.append(result)
        except Exception as e:
            errors.append({
                "claim_id": claim.claim_id,
                "error":    str(e)
            })

    return {
        "total":     len(batch.claims),
        "processed": len(results),
        "errors":    len(errors),
        "results":   results,
        "error_details": errors,
    }


@router.post(
    "/adjudicate/upload/csv",
    tags=["Claims"],
    summary="Upload a CSV file of claims",
    description="Upload a CSV file. Each row is adjudicated and results returned."
)
async def adjudicate_csv(file: UploadFile = File(...)):
    """
    CSV file upload endpoint.
    Reads each row as a claim, adjudicates it,
    and returns all results.
    """
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
                "row":   int(row.get("claim_id", "unknown")),
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


