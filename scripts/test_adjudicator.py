from engine.adjudicator import adjudicate
import json

# Test 1 — should Pass
legitimate_claim = {
    "claim_id":                "CLM-TEST-001",
    "member_id":               "MEM-00001",
    "provider_id":             "PRV-00001",
    "diagnosis_code":          "B50.9",
    "procedure_code":          "99214",
    "claimed_amount":          4200,
    "approved_tariff":         4000,
    "date_of_service":         "2026-02-01T10:00:00",
    "provider_type":           "hospital",
    "location":                "Nairobi",
    "member_age":              34,
    "member_claim_frequency":  2,
    "provider_claim_frequency": 8,
    "is_duplicate":            0,
}

# Test 2 — should Fail (stage 2 hard override)
inflated_claim = {**legitimate_claim,
    "claim_id":       "CLM-TEST-002",
    "claimed_amount": 50000,  # 12.5x the tariff
}

# Test 3 — should Flag (for ML scoring)
suspicious_claim = {**legitimate_claim,
    "claim_id":                "CLM-TEST-003",
    "procedure_code":          "43239",  # mismatched procedure
    "claimed_amount":          5800,
    "provider_id":             "PRV-00003",
    "provider_claim_frequency": 35,
    "member_claim_frequency":  12,
}

for claim in [legitimate_claim, inflated_claim, suspicious_claim]:
    print(f"\n{'='*55}")
    print(f"Testing claim: {claim['claim_id']}")
    result = adjudicate(claim)
    print(f"Decision     : {result['decision']}")
    print(f"Risk Score   : {result['risk_score']}")
    print(f"Confidence   : {result['confidence']}")
    print(f"Stage        : {result['adjudication_stage']}")
    print(f"Reasons:")
    for r in result["reasons"]:
        print(f"  • {r}")
    print(f"Processing   : {result['processing_time_ms']}ms")