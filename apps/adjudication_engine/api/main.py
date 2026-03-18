import os
import sys
import json
import pickle
import xgboost as xgb

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from api.routes import claims, health
from api.routes.auth import router as auth_router
from api.routes.documents import router as documents_router
from api.middleware import (
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
)
from monitoring.logger import get_logger
from monitoring.metrics import (
    claims_total, adjudication_duration, risk_score_histogram,
    http_requests_total, active_requests, generate_latest, CONTENT_TYPE_LATEST,
)
import time
from dotenv import load_dotenv

load_dotenv()

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Ginja Claims Adjudication Engine")

    try:
        model = xgb.XGBClassifier()
        model.load_model("model/artifacts/xgboost_model.json")

        with open("model/artifacts/shap_explainer.pkl", "rb") as f:
            explainer = pickle.load(f)

        with open("model/artifacts/feature_columns.json") as f:
            feature_columns = json.load(f)

        app.state.model = model
        app.state.explainer = explainer
        app.state.feature_columns = feature_columns

        logger.info("Model artifacts loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load model artifacts: {e}")
        raise

    yield

    logger.info("Shutting down Ginja Claims Adjudication Engine")


app = FastAPI(
    title = "Ginja Claims Adjudication Engine",
    description = """
        AI-powered healthcare claims adjudication for East Africa (Kenya and Rwanda).

        ## Auth
        All endpoints except /health require an API key in the X-API-Key header.

        ## Decision Logic
        | Risk Score | Decision |
        |------------|----------|
        | 0.0 to 0.3 -> Pass
        | 0.3 to 0.7 -> Flag
        | 0.7 to 1.0 -> Fail

        ## Adjudication Stages
        1. Basic validation (format, completeness, date checks)
        2. Clinical validation (code checks, financial hard rules)
        3. ML scoring (XGBoost + SHAP explainability)
    """,
    version = "1.0.0",
    docs_url = "/docs",
    redoc_url = "/redoc",
    lifespan = lifespan,
)

# Middleware
@app.middleware("http")
async def metrics_middleware(request, call_next):
    active_requests.inc()
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    http_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
    ).inc()

    active_requests.dec()
    return response

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=640)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins  = os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_methods  = ["GET", "POST"],
    allow_headers  = ["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catches any unhandled exception and returns a structured
    error response rather than exposing a stack trace.

    Stack traces must never be returned to API clients in
    production as they reveal internal implementation details.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}",
        extra={"request_id": request_id, "error": str(exc)}
    )
    return JSONResponse(
        status_code = 500,
        content = {
            "error": "Internal server error",
            "request_id": request_id,
            "message": "An unexpected error occurred. Quote the request_id when reporting this issue.",
        }
    )

@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

app.include_router(health.router, prefix="/api/v1")
app.include_router(claims.router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")


@app.get("/", tags=["System"], include_in_schema=False)
async def root():
    return {
        "service": "Ginja Claims Adjudication Engine",
        "version": "1.0.0",
        "region": "East Africa (Kenya, Rwanda)",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
