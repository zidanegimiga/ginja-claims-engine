"""
Model Retraining Pipeline

This script retrains the XGBoost model on an updated dataset
and registers the new version in the model registry.

Retraining should be triggered when:
1. Drift detection reports PSI >= 0.2 on key features
2. Model precision drops below 0.85 on recent labelled claims
3. A scheduled retraining interval is reached (e.g. monthly)
4. A significant new fraud pattern is identified

MLOps principle: retraining is not automatic promotion.
The new model is registered as 'staging' and must pass
evaluation gates before being promoted to production.

Usage:
    python scripts/retrain.py
    python scripts/retrain.py --data data/synthetic/claims_training.csv
    python scripts/retrain.py --promote  # auto-promote if metrics improve
"""

import sys
import os
import argparse
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from model.train import (
    load_training_data,
    prepare_features,
    train_model,
    evaluate_model,
    compute_shap_values,
    save_artifacts,
    FEATURE_COLUMNS,
)
from model.registry import (
    register_model,
    promote_to_production,
    get_production_model,
)
from model.drift import detect_drift, log_drift_report
from sklearn.model_selection import train_test_split
from datetime import datetime, timezone


MINIMUM_ACCEPTABLE_ROC_AUC = 0.85
MINIMUM_ACCEPTABLE_RECALL  = 0.80


def run_retraining(
    data_path:    str  = "data/synthetic/claims_training.csv",
    auto_promote: bool = False,
) -> str:
    """
    Full retraining pipeline.

    1. Check current drift status
    2. Load updated training data
    3. Train new model
    4. Evaluate against minimum thresholds
    5. Register in model registry
    6. Optionally promote to production

    Returns the version ID of the newly trained model.
    """
    print("=" * 55)
    print("GINJA CLAIMS — MODEL RETRAINING PIPELINE")
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 55)

    # Step 1 — Check drift before retraining
    print("\n[1/6] Checking feature drift...")
    drift_report = detect_drift(data_path)
    log_drift_report(drift_report)

    if drift_report.get("drift_detected"):
        print(f"  Drift detected: {drift_report['recommendation']}")
        for alert in drift_report.get("alerts", []):
            print(f"  {alert['severity'].upper()}: {alert['description']}")
    else:
        print(f"  No significant drift detected")
        if not auto_promote:
            confirm = input("  No drift detected. Continue retraining anyway? [y/N]: ")
            if confirm.lower() != "y":
                print("  Retraining cancelled")
                return ""

    # Step 2 — Load data
    print("\n[2/6] Loading training data...")
    dataframe = load_training_data(data_path)

    # Step 3 — Prepare features
    print("\n[3/6] Preparing features...")
    X, y = prepare_features(dataframe)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Step 4 — Train
    print("\n[4/6] Training model...")
    model = train_model(X_train, y_train)

    # Step 5 — Evaluate
    print("\n[5/6] Evaluating model...")
    metrics = evaluate_model(model, X_test, y_test)

    # Check against minimum thresholds
    if metrics["roc_auc"] < MINIMUM_ACCEPTABLE_ROC_AUC:
        print(
            f"  FAILED: ROC-AUC {metrics['roc_auc']} is below "
            f"minimum threshold {MINIMUM_ACCEPTABLE_ROC_AUC}"
        )
        print("  Model NOT registered. Check training data quality.")
        return ""

    if metrics["recall"] < MINIMUM_ACCEPTABLE_RECALL:
        print(
            f"  FAILED: Recall {metrics['recall']} is below "
            f"minimum threshold {MINIMUM_ACCEPTABLE_RECALL}"
        )
        print("  Model NOT registered. Too many fraud cases would be missed.")
        return ""

    print(f"  Evaluation passed: ROC-AUC={metrics['roc_auc']}, Recall={metrics['recall']}")

    # Compare against current production model
    current_production = get_production_model()
    if current_production:
        current_auc = current_production["metrics"].get("roc_auc", 0)
        if metrics["roc_auc"] < current_auc - 0.02:
            print(
                f"  WARNING: New model ROC-AUC ({metrics['roc_auc']}) is "
                f"more than 0.02 below current production ({current_auc})"
            )
            if not auto_promote:
                confirm = input("  Register anyway? [y/N]: ")
                if confirm.lower() != "y":
                    return ""

    # Step 5b — SHAP
    explainer, _, feature_importance = compute_shap_values(model, X_train, X_test)

    # Save artifacts
    model_path = "model/artifacts/xgboost_model.json"
    save_artifacts(model, explainer, metrics, feature_importance)

    # Step 6 — Register
    print("\n[6/6] Registering model...")
    training_params = {
        "n_estimators":      200,
        "max_depth":         4,
        "learning_rate":     0.05,
        "subsample":         0.8,
        "colsample_bytree":  0.8,
        "algorithm":         "XGBoost",
    }

    version_id = register_model(
        model_path         = model_path,
        metrics            = metrics,
        feature_columns    = FEATURE_COLUMNS,
        training_params    = training_params,
        training_data_path = data_path,
        description        = f"Retrained on {datetime.now().strftime('%Y-%m-%d')}. {drift_report.get('recommendation', '')}",
    )

    if auto_promote:
        print(f"\nAuto-promoting {version_id} to production...")
        promote_to_production(version_id)
    else:
        print(f"\nModel {version_id} registered as 'staging'")
        print("To promote to production run:")
        print(f"  from model.registry import promote_to_production")
        print(f"  promote_to_production('{version_id}')")

    print("\n" + "=" * 55)
    print("RETRAINING PIPELINE COMPLETE")
    print("=" * 55)

    return version_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retrain the claims adjudication model")
    parser.add_argument("--data",    default="data/synthetic/claims_training.csv")
    parser.add_argument("--promote", action="store_true", help="Auto-promote if metrics pass")
    args = parser.parse_args()

    run_retraining(data_path=args.data, auto_promote=args.promote)