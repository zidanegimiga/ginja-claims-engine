from datetime import datetime


HIGH_RISK_PROVIDERS = {
    f"PRV-{str(i).zfill(5)}"
    for i in [3, 7, 12, 18, 24, 31, 37, 43]
}

VALID_PROCEDURE_TARIFFS = {
    "99212": 1500, "99213": 2500, "99214": 4000,
    "99215": 6000, "71046": 3500, "83036": 1800,
    "82947": 800, "93000": 2500, "81003": 600,
    "87798": 1200, "87998": 1500, "76805": 4500,
    "43239": 18000, "94640": 2000, "59400": 35000,
}

DIAGNOSIS_PROCEDURE_MAP = {
    "J06.9": ["99213", "99214"],
    "A09": ["99213", "99214", "43239"],
    "B50.9": ["99214", "99215", "87798"],
    "J18.9": ["99215", "71046", "94640"],
    "E11.9": ["99214", "83036", "82947"],
    "I10": ["99213", "93000", "83036"],
    "K29.7": ["99213", "43239"],
    "N39.0": ["99213", "81003"],
    "A01.0": ["99214", "87998"],
    "Z34.00": ["99212", "76805", "59400"],
}


def engineer_features(claim: dict) -> dict:
    """
    Computes all ML features from a raw claim dictionary.

    This function must produce the exact same features
    in the exact same way as the training data generator.
    Any mismatch causes the model to score incorrectly —
    this is called 'training-serving skew' and is one of
    the most common bugs in ML systems.
    """
    claimed = float(claim.get("claimed_amount", 0))
    tariff = float(
        claim.get("approved_tariff") or
        VALID_PROCEDURE_TARIFFS.get(claim.get("procedure_code", ""), 0) or
        claim.get("claimed_amount") or  # use claimed as proxy if nothing else
        1
    )

    # Prevent division by zero
    if tariff == 0:
        tariff = 1.0

    amount_deviation = round((claimed - tariff) / tariff, 4)
    amount_ratio = round(claimed / tariff, 4)

    diagnosis = claim.get("diagnosis_code", "")
    procedure = claim.get("procedure_code", "")
    valid_procs = DIAGNOSIS_PROCEDURE_MAP.get(diagnosis, [])
    code_match = 1 if procedure in valid_procs else 0

    provider_id = claim.get("provider_id", "")
    provider_is_high_risk = 1 if provider_id in HIGH_RISK_PROVIDERS else 0

    member_claim_frequency = int(claim.get("member_claim_frequency") or 1)
    provider_claim_frequency = int(claim.get("provider_claim_frequency") or 1)
    is_duplicate = int(claim.get("is_duplicate") or 0)
    member_age = int(claim.get("member_age") or 35)

    return {
        "amount_deviation_pct": amount_deviation,
        "amount_ratio": amount_ratio,
        "code_match": code_match,
        "member_claim_frequency": member_claim_frequency,
        "provider_claim_frequency": provider_claim_frequency,
        "provider_is_high_risk": provider_is_high_risk,
        "is_duplicate": is_duplicate,
        "member_age": member_age,
    }