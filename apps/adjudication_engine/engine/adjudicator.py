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
    if not raw_claim.get("claim_id"):
        import uuid
        raw_claim["claim_id"] = f"CLM-{uuid.uuid4().hex[:8].upper()}"


    audit_trail = []

    # ----- STAGE 1
    stage_one = run_stage_one(raw_claim)
    audit_trail.append({
        "stage": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": stage_one["passed"],
        "checks_run": stage_one["checks_run"],
        "failures": stage_one["failures"],
    })

    if not stage_one["passed"]:
        return _build_result(
            raw_claim = raw_claim,
            decision = "Fail",
            risk_score = 1.0,
            confidence = 1.0,
            reasons = stage_one["failures"],
            stage_failed = 1,
            audit_trail = audit_trail,
            started_at  = started_at,
            feature_contributions = {},
        )

    # ------ STAGE 2
    stage_two = run_stage_two(raw_claim)
    audit_trail.append({
        "stage": 2,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": stage_two["passed"],
        "checks_run": stage_two["checks_run"],
        "failures": stage_two["failures"],
        "hard_overrides": stage_two["hard_overrides"],
        "soft_flags": stage_two.get("soft_flags", []),
    })

    if not stage_two["passed"]:
        return _build_result(
            raw_claim = raw_claim,
            decision = "Fail",
            risk_score = 1.0,
            confidence = 1.0,
            reasons = stage_two["failures"],
            stage_failed = 2,
            audit_trail = audit_trail,
            started_at = started_at,
            feature_contributions = {},
        )

    if stage_two["hard_overrides"]:
        return _build_result(
            raw_claim    = raw_claim,
            decision     = "Fail",
            risk_score   = 1.0,
            confidence   = 1.0,
            reasons      = stage_two["hard_overrides"],
            stage_failed = 2,
            audit_trail  = audit_trail,
            started_at   = started_at,
            feature_contributions = {},
        )
    
    # Soft flags from Stage 2 are passed into the final result
    # as additional reasons — they nudge the decision toward Flag
    # but don't override the ML score entirely
    stage_two_flags = stage_two.get("soft_flags", [])


    # ------- STAGE 3: ML Scoring
    
    # If cross-reference was run on multiple documents, incorporate those fraud signals into the final decision
    cross_ref_signals = raw_claim.get("cross_ref_fraud_signals", [])
    cross_ref_score   = float(raw_claim.get("cross_ref_score") or 0)

    features = engineer_features(raw_claim)
    ml_result = predict_claim(features)

    # Blend ML score with cross-reference score
    # Cross-reference mismatches add direct evidence of fraud
    # Weight: 70% ML score, 30% cross-reference score
    if cross_ref_score > 0:
        blended_score = round(
            (ml_result["risk_score"] * 0.7) + (cross_ref_score * 0.3), 4
        )
    else:
        blended_score = ml_result["risk_score"]
    
    from model.predict import score_to_decision

    final_decision = score_to_decision(blended_score)
    all_reasons = ml_result["reasons"] + cross_ref_signals + stage_two_flags

    if stage_two_flags and final_decision == "Pass":
        final_decision = "Flag"
        blended_score  = max(blended_score, 0.35)
        all_reasons  = [
            "Claim escalated to manual review due to missing clinical codes"
        ] + stage_two_flags + cross_ref_signals

    audit_trail.append({
        "stage": 3,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ml_score": ml_result["risk_score"],
        "cross_ref_score": cross_ref_score,
        "blended_score": blended_score,
        "confidence": ml_result["confidence"],
        "decision": final_decision,
    })

    return _build_result(
        raw_claim = raw_claim,
        decision = final_decision,
        risk_score = blended_score,
        confidence = ml_result["confidence"],
        reasons = all_reasons,
        stage_failed = None,
        audit_trail = audit_trail,
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
        **raw_claim,
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