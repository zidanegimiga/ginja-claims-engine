"""
Model Registry

Tracks all trained model versions, their performance metrics,
and which version is currently active in production.

In production this would connect to MLflow, Weights and Biases,
or a cloud-native registry like GCP Vertex AI Model Registry.
For the prototype we use MongoDB as the registry store,
which keeps the architecture consistent and avoids extra dependencies.

MLOps principle: every model that makes decisions in production
must be traceable — who trained it, on what data, with what
parameters, and what performance it achieved.
"""

import os
import json
import uuid
import hashlib
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()


def get_registry_collection():
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client[settings.MONGODB_DB_NAME]
    return db["model_registry"], client


def register_model(
    model_path: str,
    metrics: dict,
    feature_columns: list,
    training_params: dict,
    training_data_path: str,
    description: str = "",
) -> str:
    """
    Registers a newly trained model in the model registry.

    Returns the version ID assigned to this model.

    Every registered model gets:
    - A unique version ID
    - A content hash of the model file (for integrity verification)
    - Full training metadata
    - Performance metrics
    - Timestamp and status
    """
    collection, client = get_registry_collection()

    # Generate content hash for model integrity verification
    # If the model file is tampered with, the hash will not match
    model_hash = _hash_file(model_path)

    version_id = f"v{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    record = {
        "version_id": version_id,
        "model_path": model_path,
        "model_hash": model_hash,
        "status": "staging",  # staging -> production -> retired
        "description": description,
        "metrics": {
            "precision": metrics.get("precision"),
            "recall": metrics.get("recall"),
            "f1_score": metrics.get("f1_score"),
            "roc_auc": metrics.get("roc_auc"),
            "cv_roc_auc_mean": metrics.get("cv_roc_auc_mean"),
            "cv_roc_auc_std": metrics.get("cv_roc_auc_std"),
        },
        "training_params": training_params,
        "feature_columns": feature_columns,
        "training_data_path": training_data_path,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "promoted_at": None,
        "retired_at": None,
        "trained_by": os.getenv("TRAINER_ID", "system"),
    }

    collection.insert_one(record)
    client.close()

    print(f"Model registered: {version_id}")
    return version_id


def promote_to_production(version_id: str) -> None:
    """
    Promotes a model version from staging to production.

    This retires the currently active production model
    and activates the new version.

    MLOps principle: promotion should be a deliberate,
    audited action — not automatic. A human or automated
    evaluation gate should approve promotion.
    """
    collection, client = get_registry_collection()

    # Retire current production model
    collection.update_many(
        {"status": "production"},
        {"$set": {
            "status": "retired",
            "retired_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    # Promote new version
    collection.update_one(
        {"version_id": version_id},
        {"$set": {
            "status": "production",
            "promoted_at": datetime.now(timezone.utc).isoformat(),
        }}
    )

    client.close()
    print(f"Model {version_id} promoted to production")


def get_production_model() -> dict | None:
    """
    Returns the currently active production model record.
    Used at API startup to verify model integrity.
    """
    collection, client = get_registry_collection()
    record = collection.find_one({"status": "production"}, {"_id": 0})
    client.close()
    return record


def get_model_history(limit: int = 10) -> list[dict]:
    """
    Returns recent model version history for the dashboard.
    """
    collection, client = get_registry_collection()
    records = list(
        collection.find({}, {"_id": 0})
        .sort("trained_at", -1)
        .limit(limit)
    )
    client.close()
    return records


def verify_model_integrity(model_path: str, expected_hash: str) -> bool:
    """
    Verifies that the model file has not been tampered with
    by comparing its content hash against the registered hash.

    Called at API startup as a security check.
    """
    actual_hash = _hash_file(model_path)
    return actual_hash == expected_hash


def _hash_file(path: str) -> str:
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
