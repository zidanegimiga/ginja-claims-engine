from datetime import datetime, timezone
from features.engineer import engineer_features
from model.predict import predict_claim
from engine.rules import run_stage_one, run_stage_two


EOB_TEMPLATES = {
    "Pass": (
        "This claim has been reviewed and approved for payment. "
        "The submitted amount is within the approved tariff range, "
        "the diagnosis and procedure codes are consistent, "
        "and no anomalies were detected."
    ),
    "Flag": (
        "This claim has been flagged for manual review before payment. "
        "One or more risk signals were detected that require verification "
        "by a benefits coordinator. The claim is not denied — it is pending "
        "further review. The provider or member may be contacted for "
        "supporting documentation."
    ),
    "Fail": (
        "This claim has been declined. The submitted information contains "
        "one or more issues that prevent approval under the current plan terms. "
        "The provider or member may appeal this decision by submitting "
        "supporting documentation within 30 days."
    ),
}


def adjudicate(raw_claim: dict) -> dict:
    """
    Main adjudication function. Orchestrates all three stages:

    Stage 1 -> Basic validation (rules only)
    Stage 2 -> Detailed validation (rules only)
    Stage 3 -> ML scoring + final decision

    A claim that fails Stage 1 never reaches Stage 2.
    A claim that fails Stage 2 never reaches ML scoring.
    This mirrors real adjudication workflow and is
    computationally efficient.

    raw_claim: the raw claim fields as received from
               the API, CSV, or PDF extraction.
               Does NOT need pre-computed features.
    """
    started_at  = datetime.now(timezone.utc)
    audit_trail = []

    # STAGE 1
    stage_one = run_stage_one(raw_claim)
    audit_trail.append({
        "stage":      1,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        "passed":     stage_one["passed"],
        "checks_run": stage_one["checks_run"],
        "failures":   stage_one["failures"],
    })

    if not stage_one["passed"]:
        return _build_result(
            raw_claim   = raw_claim,
            decision    = "Fail",
            risk_score  = 1.0,
            confidence  = 1.0,
            reasons     = stage_one["failures"],
            stage_failed = 1,
            audit_trail = audit_trail,
            started_at  = started_at,
            feature_contributions = {},
        )

    # STAGE 2
    stage_two = run_stage_two(raw_claim)
    audit_trail.append({
        "stage": 2,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": stage_two["passed"],
        "checks_run": stage_two["checks_run"],
        "failures": stage_two["failures"],
        "hard_overrides": stage_two["hard_overrides"],
    })

    if not stage_two["passed"]:
        return _build_result(
            raw_claim = raw_claim,
            decision  = "Fail",
            risk_score = 1.0,
            confidence = 1.0,
            reasons = stage_two["failures"],
            stage_failed = 2,
            audit_trail = audit_trail,
            started_at = started_at,
            feature_contributions = {},
        )

    # Hard override. Auto Fail regardless of ML score
    if stage_two["hard_overrides"]:
        return _build_result(
            raw_claim  = raw_claim,
            decision  = "Fail",
            risk_score  = 1.0,
            confidence = 1.0,
            reasons = stage_two["hard_overrides"],
            stage_failed = 2,
            audit_trail  = audit_trail,
            started_at = started_at,
            feature_contributions = {},
        )

    # STAGE 3
    features    = engineer_features(raw_claim)
    ml_result   = predict_claim(features)

    audit_trail.append({
        "stage": 3,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        "risk_score": ml_result["risk_score"],
        "confidence": ml_result["confidence"],
        "decision": ml_result["decision"],
    })

    return _build_result(
        raw_claim  = raw_claim,
        decision = ml_result["decision"],
        risk_score   = ml_result["risk_score"],
        confidence  = ml_result["confidence"],
        reasons = ml_result["reasons"],
        stage_failed = None,
        audit_trail  = audit_trail,
        started_at = started_at,
        feature_contributions = ml_result["feature_contributions"],
        features = features,
    )


def _build_result(
    raw_claim: dict,
    decision: str,
    risk_score: float,
    confidence: float,
    reasons: list,
    stage_failed: int | None,
    audit_trail: list,
    started_at: datetime,
    feature_contributions: dict,
    features: dict = {},
) -> dict:
    """
    Assembles the final adjudication result document.
    This is what gets saved to MongoDB and returned by the API.
    """
    finished_at = datetime.now(timezone.utc)
    processing_ms = int(
        (finished_at - started_at).total_seconds() * 1000
    )

    eob = EOB_TEMPLATES.get(decision, "")
    if reasons and decision != "Pass":
        eob += f" Specific issues identified: {'; '.join(reasons)}."

    return {
        "claim_id": raw_claim.get("claim_id"),
        "member_id": raw_claim.get("member_id"),
        "provider_id": raw_claim.get("provider_id"),
        "decision": decision,
        "risk_score": risk_score,
        "confidence": confidence,
        "reasons": reasons,
        "explanation_of_benefits": eob,
        "feature_contributions": feature_contributions,
        "features_used": features,
        "adjudication_stage": stage_failed or 3,
        "audit_trail": audit_trail,
        "processing_time_ms": processing_ms,
        "adjudicated_at": finished_at.isoformat(),
    }