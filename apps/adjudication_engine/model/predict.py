import json
import pickle
import numpy as np
import pandas as pd
import xgboost as xgb
from dotenv import load_dotenv

load_dotenv()

# THRESHOLDS
# These map a probability score to a decision.
# 0.0 – 0.3  -> Pass  (likely legitimate)
# 0.3 – 0.7 -> Flag  (needs human review)
# 0.7 – 1.0 -> Fail  (likely fraud)

THRESHOLD_PASS = 0.3
THRESHOLD_FAIL = 0.7


def load_model_artifacts():
    """
    Loads the trained model and SHAP explainer from disk.
    Called once at API startup, not on every request.
    """
    model = xgb.XGBClassifier()
    model.load_model("model/artifacts/xgboost_model.json")

    with open("model/artifacts/shap_explainer.pkl", "rb") as f:
        explainer = pickle.load(f)

    with open("model/artifacts/feature_columns.json") as f:
        feature_columns = json.load(f)

    return model, explainer, feature_columns


def score_to_decision(probability: float) -> str:
    """
    Maps a raw probability score to a human-readable decision.

    probability: float between 0.0 and 1.0 higher = more likely to be fraud
    """
    if probability < THRESHOLD_PASS:
        return "Pass"
    elif probability < THRESHOLD_FAIL:
        return "Flag"
    else:
        return "Fail"


def compute_confidence(probability: float) -> float:
    """
    Confidence measures how certain the model is about its decision, regardless of which decision it made.

    A score of 0.15 -> confident it's legitimate (confidence = 0.85)
    A score of 0.85 -> confident it's fraud (confidence = 0.85)
    A score of 0.50 -> completely uncertain (confidence = 0.0)

    This is different from the risk score itself.
    Risk score = how fraudulent
    Confidence = how certain
    """
    # Distance from 0.5 the point of maximum uncertainty
    # multiplied by 2 to normalise to 0–1 range
    return round(abs(probability - 0.5) * 2, 4)


def get_shap_contributions(
    explainer,
    feature_values: pd.DataFrame,
    feature_columns: list[str],
) -> dict:
    """
    Computes SHAP values for a single claim.

    Returns a dictionary mapping each feature name
    to its contribution to the fraud score.

    Positive contribution = pushed score toward fraud
    Negative contribution = pushed score toward legitimate
    """
    shap_values = explainer.shap_values(feature_values)

    contributions = {}
    for i, col in enumerate(feature_columns):
        contributions[col] = round(float(shap_values[0][i]), 4)

    # Sort by absolute contribution — most impactful first
    contributions = dict(
        sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)
    )
    return contributions


def build_reasons(
    contributions: dict,
    claim_features: dict,
    decision: str,
) -> list[str]:
    """
    Converts SHAP contributions into human-readable reason strings.
    """
    reasons = []

    amount_dev = claim_features.get("amount_deviation_pct", 0)
    if abs(amount_dev) > 0.2 and contributions.get("amount_deviation_pct", 0) > 0:
        pct = round(amount_dev * 100, 1)
        reasons.append(
            f"Claimed amount is {pct}% above the approved tariff"
        )

    if claim_features.get("code_match", 1) == 0 and contributions.get("code_match", 0) > 0:
        reasons.append(
            "Procedure code does not match the submitted diagnosis code"
        )

    if claim_features.get("provider_is_high_risk", 0) == 1:
        reasons.append(
            "Provider has an elevated risk profile based on historical claim patterns"
        )

    freq = claim_features.get("provider_claim_frequency", 0)
    if freq > 20 and contributions.get("provider_claim_frequency", 0) > 0:
        reasons.append(
            f"Provider has submitted {freq} claims — significantly above average"
        )

    if claim_features.get("is_duplicate", 0) == 1:
        reasons.append(
            "This claim matches a duplicate fingerprint — same member, provider, date, and procedure"
        )

    member_freq = claim_features.get("member_claim_frequency", 0)
    if member_freq > 10 and contributions.get("member_claim_frequency", 0) > 0:
        reasons.append(
            f"Member has submitted {member_freq} claims in the past 12 months"
        )

    # If no specific reasons triggered, give a general one
    if not reasons:
        if decision == "Pass":
            reasons.append("Claim meets all validation criteria")
        else:
            reasons.append(
                "Claim shows a combination of low-level risk signals requiring review"
            )

    return reasons


def predict_claim(claim_features: dict) -> dict:
    """
    Main prediction function. Takes a dictionary of claim features
    and returns a full adjudication result.

    This is called by the decision engine for every claim
    that passes the Stage 1 rules check.

    claim_features: dict containing the engineered features (not raw claim fields — features must be computed before calling this function)
    """
    model, explainer, feature_columns = load_model_artifacts()

    # Build a single-row dataframe in the exact column order
    # the model was trained on, order matters
    feature_row = pd.DataFrame([{
        col: claim_features.get(col, 0)
        for col in feature_columns
    }])

    # Get probability score, index [0][1] means:
    # first (only) row, probability of class 1 (fraud)
    probability = float(model.predict_proba(feature_row)[0][1])

    decision   = score_to_decision(probability)
    confidence = compute_confidence(probability)

    contributions = get_shap_contributions(explainer, feature_row, feature_columns)
    reasons       = build_reasons(contributions, claim_features, decision)

    return {
        "risk_score": round(probability, 4),
        "confidence": confidence,
        "decision": decision,
        "feature_contributions": contributions,
        "reasons": reasons,
    }


if __name__ == "__main__":
    # Quick smoke test, score one synthetic claim to verify the prediction pipeline works end to end

    test_claim = {
        "amount_deviation_pct": 1.94, # 194% above tariff, very suspicious
        "amount_ratio":  2.94,
        "code_match": 0, # codes don't match
        "member_claim_frequency":  3,
        "provider_claim_frequency": 28, # high volume provider
        "provider_is_high_risk":   1,  # flagged provider
        "is_duplicate": 0,
        "member_age": 45,
    }

    print("Running prediction on test claim...")
    result = predict_claim(test_claim)

    print(f"\nDecision : {result['decision']}")
    print(f"Risk Score : {result['risk_score']}")
    print(f"Confidence : {result['confidence']}")
    print(f"\nReasons:")
    for r in result["reasons"]:
        print(f"  • {r}")
    print(f"\nFeature Contributions (SHAP):")
    for feature, value in result["feature_contributions"].items():
        direction = "-> fraud" if value > 0 else "-> legitimate"
        print(f"  {feature:<30} {value:>8.4f}  {direction}")