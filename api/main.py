import os
import sys
import time
import xgboost as xgb
import pickle
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.routes import claims, health
from dotenv import load_dotenv

load_dotenv()

# APP INITIALISATION

app = FastAPI(
    title       = "Ginja Claims Adjudication Engine",
    description = """
AI-powered healthcare claims adjudication system for emerging markets.

## Capabilities
- **Single claim adjudication** via JSON payload
- **Batch adjudication** via JSON array or CSV upload
- **PDF claim extraction** via vision model (Gemini / Ollama / Qwen)
- **Three-stage adjudication**: basic validation → detailed validation → ML scoring
- **Full audit trail** saved to MongoDB

## Decision Logic
| Risk Score | Decision |
|------------|----------|
| 0.0 – 0.3  | ✅ Pass   |
| 0.3 – 0.7  | ⚠️ Flag   |
| 0.7 – 1.0  | ❌ Fail   |
    """,
    version     = "1.0.0",
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)

# CORS
# Allows the Next.js dashboard to call this API
# In production, I'd restrict origins to your domain

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)


# MODEL PRELOADING
# Load model artifacts once at startup so every request is fast — not on first request

@app.on_event("startup")
async def load_model():
    """
    Preloads the XGBoost model and SHAP explainer
    into memory when the server starts.
    Subsequent requests use the cached objects.
    """
    try:
        model = xgb.XGBClassifier()
        model.load_model("model/artifacts/xgboost_model.json")

        with open("model/artifacts/shap_explainer.pkl", "rb") as f:
            explainer = pickle.load(f)

        with open("model/artifacts/feature_columns.json") as f:
            feature_columns = json.load(f)

        # Store on app state so routes can access them
        app.state.model = model
        app.state.explainer = explainer
        app.state.feature_columns = feature_columns

        print("Model artifacts loaded successfully at startup")
    except Exception as e:
        print(f"Warning: Could not preload model: {e}")


# REQUEST TIMING MIDDLEWARE
# Adds X-Process-Time header to every responset to monitor latency from any client

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start    = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(
        round((time.time() - start) * 1000, 2)
    ) + "ms"
    return response


app.include_router(health.router,  prefix="/api/v1")
app.include_router(claims.router,  prefix="/api/v1")


@app.get("/", tags=["System"])
async def root():
    return {
        "service": "Ginja Claims Adjudication Engine",
        "version": "1.0.0",
        "docs":    "/docs",
        "health":  "/api/v1/health",
    }
