"""
Database setup script.

Creates MongoDB indexes for optimal query performance.
Run once during initial deployment or after schema changes.

Indexes are critical for production performance:
- Without an index on key_hash, every API request would
  require a full collection scan of all API keys
- Without an index on claim_id, retrieving a claim by ID
  would scan the entire claims collection
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pymongo import MongoClient, ASCENDING, DESCENDING
from dotenv import load_dotenv

load_dotenv()


def setup_indexes():
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client[os.getenv("MONGODB_DB_NAME", "ginja_claims")]

    print("Creating database indexes...")

    # fast lookup of API keys by hash on every request
    db["api_keys"].create_index(
        [("key_hash", ASCENDING)],
        unique = True,
        name = "idx_api_key_hash",
    )
    db["api_keys"].create_index(
        [("is_active", ASCENDING)],
        name = "idx_api_key_active",
    )
    print(" api_keys indexes created")

    # Claims indexes for fast retrieval and filtering
    db["claims"].create_index(
        [("claim_id", ASCENDING)],
        unique = True,
        name = "idx_claim_id",
    )
    db["claims"].create_index(
        [("decision", ASCENDING), ("adjudicated_at", DESCENDING)],
        name = "idx_decision_date",
    )
    db["claims"].create_index(
        [("member_id", ASCENDING)],
        name = "idx_member_id",
    )
    db["claims"].create_index(
        [("provider_id", ASCENDING)],
        name = "idx_provider_id",
    )
    print("  claims indexes created")

    # Auth failures for security monitoring
    db["auth_failures"].create_index(
        [("client_ip", ASCENDING), ("timestamp", DESCENDING)],
        name = "idx_auth_failures_ip",
    )
    print("  auth_failures indexes created")

    # Drift reports for chronological retrieval
    db["drift_reports"].create_index(
        [("checked_at", DESCENDING)],
        name = "idx_drift_reports_date",
    )
    print("  drift_reports indexes created")

    # Model registry
    db["model_registry"].create_index(
        [("status", ASCENDING), ("trained_at", DESCENDING)],
        name = "idx_model_registry_status",
    )
    print("  model_registry indexes created")

    client.close()
    print("\nAll indexes created successfully")


if __name__ == "__main__":
    setup_indexes()
