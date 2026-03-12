from datetime import datetime

# Fields that must be present for adjudication to proceed
REQUIRED_HARD = [
    "member_id",
    "claimed_amount",
    "date_of_service",
]

# Fields that are needed but can be flagged for manual completion
# rather than causing an immediate rejection
REQUIRED_SOFT = [
    "provider_id",
    "diagnosis_code",
    "procedure_code",
]


def validate_extracted_claim(extracted: dict) -> dict:
    """
    Validates fields extracted from a PDF.

    Hard requirements — missing these blocks adjudication:
    - member_id, claimed_amount, date_of_service

    Soft requirements — missing these flags for manual review but does not block adjudication:
    - provider_id, diagnosis_code, procedure_code

    This reflects real-world Kenyan & Rwandese claim forms which often contain descriptions rather than structured codes.
    """
    errors   = []
    warnings = list(extracted.get("extraction_warnings", []))

    # Hard required fields
    for field in REQUIRED_HARD:
        if not extracted.get(field):
            errors.append(
                f"Required field missing or unreadable: {field}"
            )

    # Soft required fields — warn but don't block
    for field in REQUIRED_SOFT:
        if not extracted.get(field):
            warnings.append(
                f"Field missing — will require manual review: {field}"
            )

    # Validate amount
    amount = extracted.get("claimed_amount")
    if amount is not None:
        try:
            if float(amount) <= 0:
                errors.append("Claimed amount must be greater than zero")
        except (TypeError, ValueError):
            errors.append(
                f"Claimed amount is not a valid number: {amount}"
            )

    # Validate date
    date_str = extracted.get("date_of_service")
    if date_str:
        try:
            datetime.fromisoformat(
                str(date_str).replace("Z", "").replace("/", "-")
            )
        except ValueError:
            warnings.append(
                f"Date format may need manual review: {date_str}"
            )

    extracted["is_valid"] = len(errors) == 0
    extracted["validation_errors"] = errors
    extracted["extraction_warnings"] = warnings

    return extracted