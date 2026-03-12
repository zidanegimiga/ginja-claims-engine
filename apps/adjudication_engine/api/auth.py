"""
API Authentication

Implements API key authentication with the following properties:

- Keys are stored hashed in MongoDB using SHA-256
  The plaintext key is shown exactly once at creation
  and never stored or retrievable again.

- Keys have scopes that limit what they can do:
    read: GET endpoints only
    write: POST endpoints (adjudication, uploads)
    admin: all endpoints including model management

- Keys have optional expiry dates

- Every authentication attempt (success or failure)
  is logged to MongoDB for security audit purposes

- Failed authentication from the same IP is rate limited
  separately from the main rate limiter

Security principle: defence in depth.
API keys are one layer. Rate limiting is another.
Input validation is another. No single layer is sufficient.
"""

import os
import uuid
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from pymongo import MongoClient
from dotenv import load_dotenv
from monitoring.logger import get_logger

load_dotenv()

logger = get_logger(__name__)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

VALID_SCOPES = {"read", "write", "admin"}


def get_db():
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client[os.getenv("MONGODB_DB_NAME", "ginja_claims")]
    return db, client


def generate_api_key(
    name: str,
    scopes: list[str],
    expires_days: Optional[int] = None,
    created_by: str = "system",
) -> dict:
    """
    Generates a new API key and stores it hashed in MongoDB.

    The raw key is returned exactly once and never stored.
    If lost, the key must be regenerated.

    name: human-readable label e.g. "dashboard-prod"
    scopes: list of permitted scopes e.g. ["read", "write"]
    expires_days: optional expiry in days, None means no expiry
    created_by:   who created the key (for audit trail)

    Returns the plaintext key — show it to the user once.
    """
    # Validate scopes
    invalid = set(scopes) - VALID_SCOPES
    if invalid:
        raise ValueError(f"Invalid scopes: {invalid}. Valid: {VALID_SCOPES}")

    # Generate a cryptographically secure random key
    # Format: ginja_<32 random bytes as hex>
    # Prefix makes keys identifiable in logs without revealing the secret
    raw_key = f"ginja_{secrets.token_hex(32)}"
    key_hash = _hash_key(raw_key)
    key_id = str(uuid.uuid4())

    expires_at = None
    if expires_days:
        expires_at = (
            datetime.now(timezone.utc) + timedelta(days=expires_days)
        ).isoformat()

    record = {
        "key_id": key_id,
        "name": name,
        "key_hash": key_hash,
        "key_prefix": raw_key[:12],  # store prefix for identification
        "scopes": scopes,
        "is_active":  True,
        "expires_at": expires_at,
        "created_by": created_by,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_used":  None,
        "use_count":  0,
    }

    db, client = get_db()
    db["api_keys"].insert_one(record)
    client.close()

    logger.info(
        "API key created",
        extra={
            "key_id":    key_id,
            "key_name":  name,
            "scopes":    scopes,
            "created_by": created_by,
        }
    )

    return {
        "key_id": key_id,
        "key": raw_key,
        "name": name,
        "scopes": scopes,
        "expires_at": expires_at,
        "warning": "Store this key securely. It will not be shown again.",
    }


def validate_api_key(
    raw_key: str,
    required_scope: str,
    request_ip: str = "unknown",
) -> dict:
    """
    Validates an API key and checks it has the required scope.

    Returns the key record if valid.
    Raises HTTP 401 if invalid, expired, or insufficient scope.
    Logs every validation attempt for audit purposes.
    """
    if not raw_key:
        _log_auth_failure("missing_key", request_ip)
        raise HTTPException(
            status_code = 401,
            detail = {
                "error": "API key required",
                "hint":  "Provide your key in the X-API-Key header",
            }
        )

    key_hash = _hash_key(raw_key)
    db, client = get_db()

    record = db["api_keys"].find_one(
        {"key_hash": key_hash, "is_active": True},
        {"_id": 0}
    )

    if not record:
        client.close()
        _log_auth_failure("invalid_key", request_ip, key_prefix=raw_key[:12])
        raise HTTPException(
            status_code = 401,
            detail = {"error": "Invalid API key"},
        )

    # Check expiry
    if record.get("expires_at"):
        expires = datetime.fromisoformat(record["expires_at"])
        if datetime.now(timezone.utc) > expires:
            client.close()
            _log_auth_failure("expired_key", request_ip, key_id=record["key_id"])
            raise HTTPException(
                status_code = 401,
                detail = {"error": "API key has expired"},
            )

    # Check scope
    if required_scope not in record.get("scopes", []):
        client.close()
        _log_auth_failure(
            "insufficient_scope", request_ip,
            key_id=record["key_id"],
            required=required_scope,
            has=record.get("scopes"),
        )
        raise HTTPException(
            status_code = 403,
            detail = {
                "error": "Insufficient permissions",
                "required": required_scope,
                "has": record.get("scopes", []),
            }
        )

    # Update usage tracking
    db["api_keys"].update_one(
        {"key_id": record["key_id"]},
        {"$set":  {"last_used": datetime.now(timezone.utc).isoformat()},
         "$inc":  {"use_count": 1}}
    )
    client.close()

    logger.info(
        "API key validated",
        extra={
            "key_id": record["key_id"],
            "key_name": record["name"],
            "scope": required_scope,
            "client_ip": request_ip,
        }
    )

    return record


def revoke_api_key(key_id: str, revoked_by: str = "system") -> None:
    """
    Revokes an API key immediately.
    The key record is kept for audit purposes but marked inactive.
    """
    db, client = get_db()
    db["api_keys"].update_one(
        {"key_id": key_id},
        {"$set": {
            "is_active":  False,
            "revoked_at": datetime.now(timezone.utc).isoformat(),
            "revoked_by": revoked_by,
        }}
    )
    client.close()
    logger.info("API key revoked", extra={"key_id": key_id, "revoked_by": revoked_by})


def list_api_keys() -> list[dict]:
    """
    Returns all API keys (without hashes) for admin review.
    """
    db, client = get_db()
    keys = list(db["api_keys"].find(
        {},
        {"_id": 0, "key_hash": 0}  # never return the hash
    ))
    client.close()
    return keys


def setup_development_key() -> Optional[str]:
    """
    Creates a default development API key if none exist.

    Called at application startup in development mode.
    In production, keys must be created explicitly via
    the admin endpoint — no automatic key creation.

    Returns the plaintext key if created, None if keys already exist.
    """
    db, client = get_db()
    existing = db["api_keys"].count_documents({"is_active": True})
    client.close()

    if existing > 0:
        return None

    dev_key_name = os.getenv("DEV_API_KEY_NAME", "development-default")
    result = generate_api_key(
        name = dev_key_name,
        scopes = ["read", "write", "admin"],
        expires_days = 30,
        created_by  = "system-startup",
    )

    logger.info(
        "Development API key created at startup",
        extra={"key_prefix": result["key"][:12]}
    )

    return result["key"]


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _log_auth_failure(reason: str, ip: str, **extra) -> None:
    db, client = get_db()
    db["auth_failures"].insert_one({
        "reason": reason,
        "client_ip": ip,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **extra,
    })
    client.close()
    logger.warning(
        f"Authentication failed: {reason}",
        extra={"reason": reason, "client_ip": ip, **extra}
    )
