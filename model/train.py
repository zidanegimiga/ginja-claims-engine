import os
import json
import pickle
import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
)
from sklearn.preprocessing import LabelEncoder
from dotenv import load_dotenv

load_dotenv()

FEATURE_COLUMNS = [
    "amount_deviation_pct",   # How far claimed amount deviates from tariff
    "amount_ratio", # Claimed vs tariff as a ratio
    "code_match",  # Does procedure match diagnosis
    "member_claim_frequency", # How often this member claims
    "provider_claim_frequency", # How often this provider submits
    "provider_is_high_risk",  # Is provider flagged
    "is_duplicate", # Duplicate fingerprint detected
    "member_age", # Age-based risk patterns
]

TARGET_COLUMN = "is_fraud"


def load_training_data(csv_path: str) -> pd.DataFrame:
    """
    Loads the synthetic training data from CSV.
    Explains what we find in it.
    """
    dataframe = pd.read_csv(csv_path)
    print(f"Loaded {len(dataframe)} claims from {csv_path}")
    print(f"Fraud rate: {dataframe[TARGET_COLUMN].mean():.1%}")
    return dataframe


def prepare_features(dataframe: pd.DataFrame):
    """
    Separates the data into:
    - X: the input features the model learns from
    - y: the answer (0=legitimate, 1=fraud) the model learns to predict
    """
    X = dataframe[FEATURE_COLUMNS].copy()
    y = dataframe[TARGET_COLUMN].copy()

    # Handle any missing values by filling with column median
    X = X.fillna(X.median())

    print(f"\nFeature matrix shape: {X.shape}")
    print(f"Features used: {FEATURE_COLUMNS}")
    return X, y


def train_model(X_train, y_train):
    """
    Trains an XGBoost model on our claims data.

    Key parameters used:
    - n_estimators: how many trees to build (200 is a good start)
    - max_depth: how deep each tree can grow (shallow = less overfitting)
    - learning_rate: how much each tree contributes (lower = more careful)
    - scale_pos_weight: compensates for imbalanced data (more legitimate than fraud)
    - eval_metric: what to optimise for during training
    """
    # Calculate class weight to handle imbalance
    # We have 3x more legitimate claims than fraud
    # This tells the model to pay extra attention to fraud cases
    fraud_count      = y_train.sum()
    legitimate_count = len(y_train) - fraud_count
    scale_weight     = legitimate_count / fraud_count

    print(f"\nClass balance — Legitimate: {legitimate_count}, Fraud: {fraud_count}")
    print(f"Scale weight applied: {scale_weight:.2f}")

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_weight,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )

    model.fit(
        X_train,
        y_train,
        verbose=False,
    )

    print("Model training complete")
    return model


def evaluate_model(model, X_test, y_test):
    """
    Measures how well the model performs on claims it
    has never seen before (the test set).

    Key metrics:
    Precision
    Recall
    F1 Score
    ROC-AUC
    """
    # Get probability scores (0.0 to 1.0)
    y_prob = model.predict_proba(X_test)[:, 1]

    # Convert probabilities to decisions using our thresholds
    # 0.0–0.3 = Pass, 0.3–0.7 = Flag, 0.7–1.0 = Fail
    y_pred = (y_prob >= 0.3).astype(int)

    print("\n" + "="*50)
    print("MODEL EVALUATION RESULTS")
    print("="*50)

    precision = precision_score(y_test, y_pred)
    recall    = recall_score(y_test, y_pred)
    f1        = f1_score(y_test, y_pred)
    roc_auc   = roc_auc_score(y_test, y_prob)

    print(f"Precision : {precision:.3f}")
    print(f"Recall    : {recall:.3f}")
    print(f"F1 Score  : {f1:.3f}")
    print(f"ROC-AUC   : {roc_auc:.3f}")

    print("\nClassification Report:")
    print(classification_report(
        y_test, y_pred,
        target_names=["Legitimate", "Fraud"]
    ))

    print("Confusion Matrix:")
    print("(Rows = Actual, Columns = Predicted)")
    print("         Predicted Legit  Predicted Fraud")
    cm = confusion_matrix(y_test, y_pred)
    print(f"Actual Legit   {cm[0][0]:>8}        {cm[0][1]:>8}")
    print(f"Actual Fraud   {cm[1][0]:>8}        {cm[1][1]:>8}")

    # Cross validation — trains and tests on 5 different splits to confirm our results are consistent, not just lucky
    print("\nRunning 5-fold cross validation...")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    X_all = pd.concat([X_test])
    cv_scores = cross_val_score(
        model,
        X_test,
        y_test,
        cv=cv,
        scoring="roc_auc"
    )
    print(f"Cross-validation ROC-AUC: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    return {
        "precision": round(precision, 3),
        "recall":    round(recall, 3),
        "f1_score":  round(f1, 3),
        "roc_auc":   round(roc_auc, 3),
        "cv_roc_auc_mean": round(cv_scores.mean(), 3),
        "cv_roc_auc_std":  round(cv_scores.std(), 3),
    }


def compute_shap_values(model, X_train, X_test):
    """
    SHAP stands for SHapley Additive exPlanations.

    It answers the question: for this specific claim, which features pushed the score up (towards fraud)
    and which pushed it down (towards legitimate)?

    For example, for a flagged claim it might say:
    - amount_deviation_pct contributed +0.38 (pushed towards fraud)
    - code_match contributed -0.12 (pushed towards legitimate)
    - provider_is_high_risk contributed +0.29 (pushed towards fraud)
    """
    print("\nComputing SHAP values for explainability...")

    explainer   = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test)

    # Global feature importance — which features matter most overall
    feature_importance = pd.DataFrame({
        "feature":   FEATURE_COLUMNS,
        "importance": np.abs(shap_values).mean(axis=0)
    }).sort_values("importance", ascending=False)

    print("\nGlobal Feature Importance (SHAP):")
    for _, row in feature_importance.iterrows():
        bar = "█" * int(row["importance"] * 100)
        print(f"  {row['feature']:<30} {row['importance']:.4f} {bar}")

    return explainer, shap_values, feature_importance


def save_artifacts(model, explainer, metrics, feature_importance):
    """
    Saves everything needed to run predictions later.

    model            — the trained XGBoost model
    explainer        — the SHAP explainer (for generating reasons)
    metrics          — evaluation scores (for the dashboard)
    feature_importance — global SHAP rankings (for the README)
    """
    os.makedirs("model/artifacts", exist_ok=True)

    # Save the model in XGBoost's native format
    model_path = "model/artifacts/xgboost_model.json"
    model.save_model(model_path)
    print(f"\nModel saved to {model_path}")

    # Save the SHAP explainer using pickle
    # Pickle serialises a Python object to a file
    explainer_path = "model/artifacts/shap_explainer.pkl"
    with open(explainer_path, "wb") as f:
        pickle.dump(explainer, f)
    print(f"SHAP explainer saved to {explainer_path}")

    # Save evaluation metrics as JSON
    metrics_path = "model/artifacts/metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Metrics saved to {metrics_path}")

    # Save feature importance
    importance_path = "model/artifacts/feature_importance.json"
    feature_importance.to_json(importance_path, orient="records", indent=2)
    print(f"Feature importance saved to {importance_path}")

    # Save feature column order — critical for prediction
    # The model expects features in exactly this order
    columns_path = "model/artifacts/feature_columns.json"
    with open(columns_path, "w") as f:
        json.dump(FEATURE_COLUMNS, f, indent=2)
    print(f"Feature columns saved to {columns_path}")


if __name__ == "__main__":
    print("="*50)
    print("GINJA CLAIMS — MODEL TRAINING PIPELINE")
    print("="*50)

    # Step 1 — Load data
    dataframe = load_training_data("data/synthetic/claims_training.csv")

    # Step 2 — Prepare features
    X, y = prepare_features(dataframe)

    # Step 3 — Split into training and test sets
    # We train on 80% of the data and test on the remaining 20%
    # stratify=y ensures both sets have the same fraud rate
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )
    print(f"\nTraining set : {len(X_train)} claims")
    print(f"Test set     : {len(X_test)} claims")

    # Step 4 — Train
    model = train_model(X_train, y_train)

    # Step 5 — Evaluate
    metrics = evaluate_model(model, X_test, y_test)

    # Step 6 — SHAP explainability
    explainer, shap_values, feature_importance = compute_shap_values(
        model, X_train, X_test
    )

    # Step 7 — Save everything
    save_artifacts(model, explainer, metrics, feature_importance)

    print("\n" + "="*50)
    print("TRAINING PIPELINE COMPLETE")
    print("="*50)