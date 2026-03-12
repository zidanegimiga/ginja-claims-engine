"""
Model Drift Detection

Drift occurs when the statistical properties of incoming claims
start to differ from the training data. This means the model
was trained on patterns that no longer reflect reality.

Two types of drift matter here:

1. Data drift (covariate shift): the distribution of input
   features changes. Example: a new fraud scheme emerges
   where amounts are only slightly above tariff rather than
   obviously inflated. The model never saw this pattern.

2. Concept drift: the relationship between features and
   fraud changes. Example: a previously low-risk provider
   type starts being used for fraud.

We detect drift by comparing the statistical distribution
of recent claims against the training data distribution.
If the distributions diverge significantly, we trigger
a retraining alert.
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv
from scipy import stats

load_dotenv()

# Thresholds for drift alerts
# These are conservative for a healthcare system where
# false negatives (missed fraud) are costly
PSI_THRESHOLD = 0.2   # Population Stability Index — standard industry threshold
PVALUE_THRESHOLD = 0.05  # Statistical significance for distribution tests
MIN_SAMPLES = 100   # Minimum recent claims needed for reliable drift detection


def compute_psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    """
    Population Stability Index (PSI).

    Measures how much a feature distribution has shifted
    between training data and recent production data.

    PSI < 0.1:  No significant shift
    PSI < 0.2:  Moderate shift — monitor closely
    PSI >= 0.2: Significant shift — consider retraining

    This is the standard metric used in credit risk and
    insurance models to monitor stability.
    """
    # Create bins from expected distribution
    breakpoints = np.linspace(
        min(expected.min(), actual.min()),
        max(expected.max(), actual.max()),
        bins + 1
    )
    breakpoints[0] -= 1e-6
    breakpoints[-1] += 1e-6

    expected_counts = np.histogram(expected, breakpoints)[0]
    actual_counts = np.histogram(actual, breakpoints)[0]

    # Replace zeros to avoid log(0)
    expected_pct = np.where(expected_counts == 0, 1e-6, expected_counts / len(expected))
    actual_pct = np.where(actual_counts == 0, 1e-6, actual_counts   / len(actual))

    psi = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
    return round(float(psi), 4)


def detect_drift(
    training_data_path: str,
    lookback_days: int = 30,
) -> dict:
    """
    Compares recent production claims against training data
    to detect feature drift.

    Returns a drift report with:
    - drift_detected: bool
    - feature_psi: PSI score per feature
    - alerts: list of features with significant drift
    - recommendation: action to take
    """
    # Load training data
    try:
        train_df = pd.read_csv(training_data_path)
    except FileNotFoundError:
        return {
            "drift_detected": False,
            "error": "Training data not found",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    # Load recent production claims from MongoDB
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client[os.getenv("MONGODB_DB_NAME", "ginja_claims")]

    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    recent_claims = list(
        db["claims"].find(
            {"adjudicated_at": {"$gte": since.isoformat()}},
            {"_id": 0, "features_used": 1}
        ).limit(5000)
    )
    client.close()

    if len(recent_claims) < MIN_SAMPLES:
        return {
            "drift_detected": False,
            "warning": f"Only {len(recent_claims)} recent claims — need {MIN_SAMPLES} for reliable drift detection",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    # Extract feature values from recent claims
    recent_features = []
    for claim in recent_claims:
        features = claim.get("features_used", {})
        if features:
            recent_features.append(features)

    if not recent_features:
        return {
            "drift_detected": False,
            "warning": "No feature data found in recent claims",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    recent_df = pd.DataFrame(recent_features)

    # Feature columns to check for drift
    feature_columns = [
        "amount_deviation_pct",
        "amount_ratio",
        "member_claim_frequency",
        "provider_claim_frequency",
        "member_age",
    ]

    feature_psi = {}
    alerts = []

    for col in feature_columns:
        if col not in train_df.columns or col not in recent_df.columns:
            continue

        train_values  = train_df[col].dropna().values
        recent_values = recent_df[col].dropna().values

        if len(recent_values) < 10:
            continue

        psi = compute_psi(train_values, recent_values)
        feature_psi[col] = psi

        if psi >= PSI_THRESHOLD:
            alerts.append({
                "feature": col,
                "psi": psi,
                "severity": "high" if psi >= 0.25 else "medium",
                "description": f"{col} distribution has shifted significantly (PSI={psi})",
            })

    drift_detected = len(alerts) > 0

    recommendation = "No action required"
    if drift_detected:
        high_severity = [a for a in alerts if a["severity"] == "high"]
        if high_severity:
            recommendation = "Immediate retraining recommended — significant feature drift detected"
        else:
            recommendation = "Schedule retraining within 2 weeks — moderate drift detected"

    return {
        "drift_detected": drift_detected,
        "features_checked": len(feature_psi),
        "feature_psi": feature_psi,
        "alerts": alerts,
        "recommendation": recommendation,
        "lookback_days": lookback_days,
        "recent_samples": len(recent_features),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def log_drift_report(report: dict) -> None:
    """
    Saves a drift detection report to MongoDB for audit trail.
    """
    try:
        client = MongoClient(os.getenv("MONGODB_URI"))
        db = client[os.getenv("MONGODB_DB_NAME", "ginja_claims")]
        db["drift_reports"].insert_one(report)
        client.close()
    except Exception as e:
        print(f"Could not save drift report: {e}")