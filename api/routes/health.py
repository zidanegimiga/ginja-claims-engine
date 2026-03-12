from fastapi import APIRouter
from api.schemas import HealthResponse
import os

router = APIRouter()

@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Simple health check endpoint.
    Used by Docker, load balancers, and monitoring to verify the service is running.
    """
    model_exists = os.path.exists("model/artifacts/xgboost_model.json")
    return HealthResponse(
        status = "healthy",
        model_loaded = model_exists,
        version = "1.0.0",
    )