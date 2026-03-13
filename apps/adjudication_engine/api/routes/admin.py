from pydantic import BaseModel
from typing import Optional
from api.auth_keys import (
    generate_api_key,
    revoke_api_key,
    list_api_keys,
    validate_api_key,
    get_client_ip,
)
from model.registry import get_model_history, get_production_model
from model.drift import detect_drift, log_drift_report
from fastapi import APIRouter, Request, Depends, HTTPException

router = APIRouter()


class CreateKeyRequest(BaseModel):
    name: str
    scopes: list[str]
    expires_days: Optional[int] = None


class RevokeKeyRequest(BaseModel):
    key_id: str


def require_admin(request: Request) -> dict:
    key = request.headers.get("X-API-Key")
    ip  = get_client_ip(request)
    return validate_api_key(key, "admin", ip)


@router.post(
    "/admin/keys",
    tags=["Admin"],
    summary="Create a new API key",
    description="Requires admin scope. The key is returned once and cannot be retrieved again.",
)
def create_key(payload: CreateKeyRequest, request: Request, auth: dict = Depends(require_admin),):
    require_admin(request)
    return generate_api_key(
        name = payload.name,
        scopes = payload.scopes,
        expires_days = payload.expires_days,
        created_by = request.headers.get("X-API-Key", "unknown")[:12],
    )


@router.get("/admin/keys", tags=["Admin"])
def get_keys(
    request: Request,
    auth: dict = Depends(require_admin),
):
    return {"keys": list_api_keys()}


@router.delete("/admin/keys/{key_id}", tags=["Admin"])
def delete_key(
    key_id: str,
    request: Request,
    auth: dict = Depends(require_admin),
):
    revoke_api_key(key_id, revoked_by=request.headers.get("X-API-Key", "unknown")[:12])
    return {"message": f"Key {key_id} revoked"}


@router.get("/admin/model/registry", tags=["Admin"])
def model_registry(
    request: Request,
    auth: dict = Depends(require_admin),
):
    return {"production": get_production_model(), "history": get_model_history()}


@router.post("/admin/model/drift", tags=["Admin"])
def run_drift_check(
    request: Request,
    auth: dict = Depends(require_admin),
):
    report = detect_drift("data/synthetic/claims_training.csv")
    log_drift_report(report)
    return report
