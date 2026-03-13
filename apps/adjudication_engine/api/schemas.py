from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime



class PatientDetails(BaseModel):
    """
    PII — stored encrypted in production.
    For this system we store as-is with RBAC as the access control layer.
    """
    full_name: Optional[str] = None
    national_id: Optional[str] = None
    date_of_birth: Optional[str] = None
    phone: Optional[str] = None
    scheme_number: Optional[str] = None  # insurance scheme / policy number

class ClaimSource(BaseModel):
    """
    Tracks how the claim entered the system.
    
    - source_type: how the claim was submitted
    - documents: up to 2 documents for cross-reference
      index 0 = primary (e.g. hospital invoice)
      index 1 = secondary (e.g. lab report or prescription)
    - cross_reference_score: agreement score between the two docs (0–1)
    """
    source_type: Literal["pdf", "csv", "json", "api", "manual"] = "api"
    document_key: Optional[str] = None    # Cloudflare R2 object key
    document_name: Optional[str] = None  # original filename
    document_url: Optional[str] = None  # presigned URL — generated on demand, not stored
    uploaded_by: Optional[str] = None  # user ID who uploaded
    uploaded_at: Optional[datetime] = None


class ClaimRequest(BaseModel):
    """
    The shape of a claim submitted via the API.
    Pydantic validates every field automatically —
    wrong types or missing required fields return
    a clear error before any processing happens.
    """
    claim_id: Optional[str] = Field(default=None, example="CLM-2024-001")
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

    patient: Optional[PatientDetails] = None
    source: Optional[ClaimSource] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("date_of_service")
    @classmethod
    def validate_date(cls, value: str) -> str:
        try:
            datetime.fromisoformat(value.replace("Z", ""))
        except ValueError:
            raise ValueError(f"Invalid date format: {value}. Use ISO format e.g. 2026-01-15T10:00:00")
        return value

    # @field_validator("member_id")
    # @classmethod
    # def validate_member_id(cls, value: str) -> str:
    #     if not value.startswith("MEM-"):
    #         raise ValueError(f"Member ID must start with MEM-: {value}")
    #     return value


class AdjudicationResponse(BaseModel):
    """
    The shape of every adjudication result returned by the API.
    """
    claim_id: str
    member_id: str
    provider_id: str
    diagnosis_code: str
    procedure_code: str
    claimed_amount: float
    approved_tariff: float
    date_of_service: str
    provider_type: str
    location: str
    member_age: Optional[int]  = None
    is_duplicate: Optional[int]  = None
    invoice_number: Optional[str]  = None
    notes: Optional[str]  = None
    patient: Optional[PatientDetails] = None
    source: Optional[ClaimSource]    = None
    decision: str
    risk_score: float
    confidence: float
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


class DocumentReference(BaseModel):
    """A single document attached to a claim."""
    document_key: str
    document_name: str
    document_type: Literal["pdf", "csv", "json", "image"]
    uploaded_by: str # user ID
    uploaded_at: datetime
    extraction_confidence: Optional[float] = None  # from the vision provider
    extraction_provider: Optional[str]  = None  # gemini, ollama, tesseract
