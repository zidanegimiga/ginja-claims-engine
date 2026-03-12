from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class ClaimRequest(BaseModel):
    """
    The shape of a claim submitted via the API.
    Pydantic validates every field automatically —
    wrong types or missing required fields return
    a clear error before any processing happens.
    """
    claim_id: str = Field(..., example="CLM-2024-001")
    member_id: str = Field(..., example="MEM-00001")
    provider_id: str = Field(..., example="PRV-00001")
    diagnosis_code: str = Field(..., example="B50.9")
    procedure_code: str = Field(..., example="99214")
    claimed_amount: float = Field(..., gt=0, example=4200.0)
    approved_tariff: float = Field(..., gt=0, example=4000.0)
    date_of_service: str = Field(..., example="2026-01-15T10:00:00")
    provider_type: str = Field(..., example="hospital")
    location: str = Field(..., example="Nairobi")
    member_age: Optional[int]   = Field(default=35, ge=0, le=120)
    member_claim_frequency:  Optional[int]   = Field(default=1,  ge=0)
    provider_claim_frequency: Optional[int]  = Field(default=1,  ge=0)
    is_duplicate: Optional[int] = Field(default=0)
    historical_claim_frequency: Optional[int] = Field(default=1, ge=0)

    @field_validator("date_of_service")
    @classmethod
    def validate_date(cls, value: str) -> str:
        try:
            datetime.fromisoformat(value.replace("Z", ""))
        except ValueError:
            raise ValueError(f"Invalid date format: {value}. Use ISO format e.g. 2026-01-15T10:00:00")
        return value

    @field_validator("member_id")
    @classmethod
    def validate_member_id(cls, value: str) -> str:
        if not value.startswith("MEM-"):
            raise ValueError(f"Member ID must start with MEM-: {value}")
        return value


class AdjudicationResponse(BaseModel):
    """
    The shape of every adjudication result returned by the API.
    """
    claim_id: str
    member_id: str
    provider_id: str
    decision: str
    risk_score:  float
    confidence:  float
    reasons: list[str]
    explanation_of_benefits: str
    feature_contributions: dict
    adjudication_stage: int
    processing_time_ms: int
    adjudicated_at: str


class BatchClaimRequest(BaseModel):
    """
    For submitting multiple claims at once via CSV or JSON array.
    """
    claims: list[ClaimRequest]


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    version: str