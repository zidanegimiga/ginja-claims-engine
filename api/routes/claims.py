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



