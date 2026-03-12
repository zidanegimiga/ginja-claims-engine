from datetime import datetime

REQUIRED_FOR_ADJUDICATION = [
    "member_id",
    "provider_id",
    "diagnosis_code",
    "procedure_code",
    "claimed_amount",
    "date_of_service",
]


def validate_extracted_claim(extracted: dict) -> dict:
    """
    Validates fields extracted from a PDF before adjudication.

    Returns the extracted dict with two added fields:
    - is_valid: bool — whether the claim can be adjudicated
    - validation_errors: list of specific problems found
    """
    errors   = []
    warnings = list(extracted.get("extraction_warnings", []))

    # Check required fields are present
    for field in REQUIRED_FOR_ADJUDICATION:
        if not extracted.get(field):
            errors.append(f"Required field missing or unreadable: {field}")

    # is amm=ount > 0 (+ve number)
    amount = extracted.get("claimed_amount")
    if amount is not None:
        try:
            if float(amount) <= 0:
                errors.append("Claimed amount must be greater than zero")
        except (TypeError, ValueError):
            errors.append(f"Claimed amount is not a valid number: {amount}")

    # Validate date format
    date_str = extracted.get("date_of_service")
    if date_str:
        try:
            datetime.fromisoformat(str(date_str).replace("Z", "").replace("/", "-"))
        except ValueError:
            warnings.append(
                f"Date format may need manual review: {date_str}"
            )

    extracted["is_valid"] = len(errors) == 0
    extracted["validation_errors"] = errors
    extracted["extraction_warnings"] = warnings

    return extracted