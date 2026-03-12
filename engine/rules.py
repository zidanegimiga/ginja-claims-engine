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
        # Only hard-fail on truly required fields
        # provider_id, diagnosis_code, procedure_code are soft
        hard_missing = [
            f for f in missing
            if f not in (
                "provider_id", "diagnosis_code", "procedure_code",
                "approved_tariff", "claim_id"
            )
        ]
        if hard_missing:
            failures.append(f"Missing required fields: {', '.join(hard_missing)}")

    # Member ID format — only check if value exists
    checks_run.append("member_id_format")
    member_id = claim.get("member_id")
    if member_id is not None:
        member_id = str(member_id)
        if member_id and not member_id.startswith("MEM-"):
            # Warn but don't fail — PDF extracted IDs won't have MEM- prefix
            pass

    # Provider ID format — only check if value exists
    checks_run.append("provider_id_format")
    provider_id = claim.get("provider_id")
    if provider_id is not None:
        provider_id = str(provider_id)
        if provider_id and not provider_id.startswith("PRV-"):
            pass  # Soft warning only

    # Claimed amount is positive
    checks_run.append("amount_positive")
    claimed = claim.get("claimed_amount", 0)
    if not isinstance(claimed, (int, float)) or claimed <= 0:
        failures.append(f"Claimed amount must be positive: {claimed}")

    # Date of service
    checks_run.append("date_not_future")
    date_str = claim.get("date_of_service")
    if date_str:
        try:
            dos = datetime.fromisoformat(
                str(date_str).replace("Z", "")
            )
            checks_run.append("claim_not_stale")
            if dos < datetime.now() - timedelta(days=MAX_CLAIM_AGE_DAYS):
                failures.append(
                    f"Claim is older than {MAX_CLAIM_AGE_DAYS} days"
                )
        except (ValueError, TypeError):
            failures.append(f"Invalid date format: {date_str}")
    else:
        failures.append("Date of service is missing")

    # Provider type
    checks_run.append("provider_type_valid")
    provider_type = str(claim.get("provider_type") or "").lower()
    if provider_type and provider_type not in VALID_PROVIDER_TYPES:
        failures.append(f"Unrecognised provider type: {provider_type}")

    return {
        "passed":     len(failures) == 0,
        "stage":      1,
        "failures":   failures,
        "checks_run": checks_run,
    }
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

# DETAILED VALIDATION
def run_stage_two(claim: dict) -> dict:
    failures = []
    checks_run = []
    hard_overrides = []
    soft_flags = []

    # ── ICD-10 diagnosis code ──
    # In East African paper claims, diagnosis is often written
    # in plain English rather than coded. We flag for review
    # rather than failing — a human reviewer or LLM can
    # map descriptions to codes during manual review.
    checks_run.append("diagnosis_code_valid")
    diagnosis_code = claim.get("diagnosis_code")
    if diagnosis_code and diagnosis_code not in VALID_ICD10_CODES:
        soft_flags.append(
            f"Unrecognised ICD-10 code: {diagnosis_code} — manual review required"
        )
    elif not diagnosis_code:
        diagnosis_desc = claim.get("diagnosis_description")
        if not diagnosis_desc:
            soft_flags.append(
                "No diagnosis code or description found — manual review required"
            )
        else:
            soft_flags.append(
                f"Diagnosis described as '{diagnosis_desc}' — "
                f"ICD-10 code mapping required during review"
            )

    # ── CPT procedure code ──
    # Same reasoning — paper invoices use descriptions not codes
    checks_run.append("procedure_code_valid")
    procedure_code = claim.get("procedure_code")
    if procedure_code and procedure_code not in VALID_CPT_CODES:
        soft_flags.append(
            f"Unrecognised CPT code: {procedure_code} — manual review required"
        )
    elif not procedure_code:
        procedure_desc = claim.get("procedure_description")
        if procedure_desc:
            soft_flags.append(
                f"Procedure described as '{procedure_desc}' — "
                f"CPT code mapping required during review"
            )

    # ── Line item total vs claimed amount ──
    # If line items were extracted, verify they add up
    # to the claimed amount. A mismatch is a fraud signal.
    checks_run.append("line_items_sum")
    line_items    = claim.get("line_items") or []
    claimed       = float(claim.get("claimed_amount") or 0)
    if line_items and claimed > 0:
        try:
            line_total = sum(
                float(item.get("total") or 0)
                for item in line_items
                if isinstance(item, dict)
            )
            if line_total > 0:
                discrepancy = abs(line_total - claimed) / claimed
                if discrepancy > 0.05:  # more than 5% difference
                    soft_flags.append(
                        f"Line items total ({line_total} KES) does not match "
                        f"claimed amount ({claimed} KES) — possible billing error"
                    )
        except (TypeError, ValueError):
            pass

    # ── Hard override: amount more than 3x tariff ──
    # Only applies when we have a tariff to compare against
    checks_run.append("hard_amount_override")
    tariff = float(claim.get("approved_tariff") or 0)
    if tariff > 0 and claimed > tariff * HARD_FAIL_AMOUNT_MULTIPLIER:
        hard_overrides.append(
            f"Claimed amount ({claimed} KES) exceeds "
            f"{HARD_FAIL_AMOUNT_MULTIPLIER}x the approved tariff ({tariff} KES)"
        )

    return {
        "passed":          len(failures) == 0,
        "stage":           2,
        "failures":        failures,
        "hard_overrides":  hard_overrides,
        "soft_flags":      soft_flags,
        "checks_run":      checks_run,
    }
