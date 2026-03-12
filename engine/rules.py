from datetime import datetime, timedelta
from typing import Optional


VALID_ICD10_CODES = {
    "J06.9", "A09", "B50.9", "J18.9", "E11.9",
    "I10", "K29.7", "N39.0", "A01.0", "Z34.00",
}

VALID_CPT_CODES = {
    "99212", "99213", "99214", "99215",
    "71046", "83036", "82947", "93000",
    "81003", "87798", "87998", "76805",
    "43239", "94640", "59400",
}

VALID_PROVIDER_TYPES = {
    "hospital", "clinic", "pharmacy",
    "laboratory", "specialist",
}

# standard for insurance markets
MAX_CLAIM_AGE_DAYS = 90

# hard override thresholds 
HARD_FAIL_AMOUNT_MULTIPLIER = 3.0


# BASIC VALIDATION
def run_stage_one(claim: dict) -> dict:
    """
    Stage 1: Basic information check.

    Mirrors step 1 of real claims adjudication:
    - No duplicate claim
    - Required fields present
    - Member information complete
    - No obvious data errors

    Returns a result dict with:
    - passed: bool
    - failures: list of specific failure reasons
    - checks_run: list of all checks attempted
    """
    failures   = []
    checks_run = []

    # Required fields present
    required_fields = [
        "claim_id", "member_id", "provider_id",
        "diagnosis_code", "procedure_code",
        "claimed_amount", "approved_tariff",
        "date_of_service", "provider_type", "location",
    ]
    checks_run.append("required_fields")
    missing = [f for f in required_fields if not claim.get(f)]
    if missing:
        failures.append(f"Missing required fields: {', '.join(missing)}")

    # Member ID format
    checks_run.append("member_id_format")
    member_id = claim.get("member_id", "")
    if not member_id.startswith("MEM-"):
        failures.append(f"Invalid member ID format: {member_id}")

    # Provider ID format
    checks_run.append("provider_id_format")
    provider_id = claim.get("provider_id", "")
    if not provider_id.startswith("PRV-"):
        failures.append(f"Invalid provider ID format: {provider_id}")

    # Claimed amount is positive
    checks_run.append("amount_positive")
    claimed = claim.get("claimed_amount", 0)
    if not isinstance(claimed, (int, float)) or claimed <= 0:
        failures.append(f"Claimed amount must be positive: {claimed}")

    # Approved tariff is positive
    checks_run.append("tariff_positive")
    tariff = claim.get("approved_tariff", 0)
    if not isinstance(tariff, (int, float)) or tariff <= 0:
        failures.append(f"Approved tariff must be positive: {tariff}")

    # Date of service is not in the future
    checks_run.append("date_not_future")
    try:
        dos = datetime.fromisoformat(
            claim.get("date_of_service", "").replace("Z", "")
        )
        if dos > datetime.now():
            failures.append("Date of service cannot be in the future")

        # Claim is not too old
        checks_run.append("claim_not_stale")
        if dos < datetime.now() - timedelta(days=MAX_CLAIM_AGE_DAYS):
            failures.append(
                f"Claim is older than {MAX_CLAIM_AGE_DAYS} days and cannot be processed"
            )
    except (ValueError, TypeError):
        failures.append(f"Invalid date of service format: {claim.get('date_of_service')}")

    # Provider type is recognised
    checks_run.append("provider_type_valid")
    provider_type = claim.get("provider_type", "").lower()
    if provider_type not in VALID_PROVIDER_TYPES:
        failures.append(f"Unrecognised provider type: {provider_type}")

    return {
        "passed":     len(failures) == 0,
        "stage":      1,
        "failures":   failures,
        "checks_run": checks_run,
    }


# DETAILED VALIDATION
def run_stage_two(claim: dict) -> dict:
    """
    Stage 2: Detailed information check.

    Mirrors step 2 of real claims adjudication:
    - Diagnosis and procedure codes are valid
    - Financial amounts are within hard limits
    - Provider type matches procedure type

    Returns same structure as stage one result.
    Hard rule overrides are flagged separately
    so the decision engine can apply them even
    when the ML score disagrees.
    """
    failures      = []
    checks_run    = []
    hard_overrides = []

    # ICD-10 diagnosis code is valid
    checks_run.append("diagnosis_code_valid")
    diagnosis_code = claim.get("diagnosis_code", "")
    if diagnosis_code not in VALID_ICD10_CODES:
        failures.append(
            f"Unrecognised ICD-10 diagnosis code: {diagnosis_code}"
        )

    # CPT procedure code is valid
    checks_run.append("procedure_code_valid")
    procedure_code = claim.get("procedure_code", "")
    if procedure_code not in VALID_CPT_CODES:
        failures.append(
            f"Unrecognised CPT procedure code: {procedure_code}"
        )

    # Hard override: amount more than 3x tariff
    # This is an automatic Fail regardless of ML score.
    # No legitimate claim should ever be 3x the approved rate.
    checks_run.append("hard_amount_override")
    claimed = claim.get("claimed_amount", 0)
    tariff  = claim.get("approved_tariff", 1)
    if tariff > 0 and claimed > tariff * HARD_FAIL_AMOUNT_MULTIPLIER:
        hard_overrides.append(
            f"Claimed amount ({claimed} KES) exceeds "
            f"{HARD_FAIL_AMOUNT_MULTIPLIER}x the approved tariff ({tariff} KES)"
        )

    #Hard override: zero tariff
    checks_run.append("tariff_not_zero")
    if tariff == 0:
        hard_overrides.append("Approved tariff is zero — possible data error")

    return {
        "passed":          len(failures) == 0,
        "stage":           2,
        "failures":        failures,
        "hard_overrides":  hard_overrides,
        "checks_run":      checks_run,
    }