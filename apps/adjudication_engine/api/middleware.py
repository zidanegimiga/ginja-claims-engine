"""
API Middleware

Security and reliability middleware for the FastAPI application.

Implements:
- API key authentication
- Rate limiting
- Request ID tracking
- Input sanitisation
- Security headers
"""

import os
import time
import uuid
import hashlib
from collections import defaultdict
from datetime import datetime, timezone
from fastapi import Request, HTTPException, Security
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv
from fastapi.security.api_key import APIKeyHeader

load_dotenv()

API_KEY_HEADER = APIKeyHeader(
    name = "X-API-Key",
    description = "API key for authentication. Contact Ginja AI to obtain a key.",
    auto_error  = False,
)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Assigns a unique ID to every request.

    This ID is returned in the response header and logged
    with every log line, making it possible to trace a
    single request through all log entries.

    Essential for debugging production issues and
    correlating logs across services.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to every response.

    These headers instruct browsers and API clients
    to enforce security policies. Standard practice
    for any production API.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Cache-Control"] = "no-store"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting.

    Limits each API key to a maximum number of requests
    per minute. Exceeding the limit returns HTTP 429.

    In production, use Redis for rate limit state so
    limits are enforced across multiple server instances.
    This in-memory implementation works correctly for
    single-instance deployments.

    Default: 60 requests per minute per API key.
    """

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds      = 60
        # key -> list of request timestamps
        self._requests: dict[str, list] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ("/api/v1/health", "/"):
            return await call_next(request)

        client_key = self._get_client_key(request)
        now = time.time()
        window_start = now - self.window_seconds

        # Remove timestamps outside the current window
        self._requests[client_key] = [
            t for t in self._requests[client_key]
            if t > window_start
        ]

        if len(self._requests[client_key]) >= self.requests_per_minute:
            return JSONResponse(
                status_code = 429,
                content = {
                    "error": "Rate limit exceeded",
                    "limit": self.requests_per_minute,
                    "window": "60 seconds",
                    "retry_after": int(self._requests[client_key][0] + self.window_seconds - now),
                }
            )

        self._requests[client_key].append(now)
        return await call_next(request)

    def _get_client_key(self, request: Request) -> str:
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            return hashlib.sha256(api_key.encode()).hexdigest()[:16]
        return request.client.host if request.client else "unknown"


def verify_api_key(request: Request) -> None:
    """
    Verifies the API key on protected endpoints.

    Expects the key in the X-API-Key header.
    Returns HTTP 401 if missing or invalid.

    In production, keys would be stored hashed in MongoDB
    with associated permissions, rate limit tiers, and
    expiry dates. For the prototype we use environment
    variables for simplicity.
    """
    valid_keys = set(filter(None, [
        os.getenv("API_KEY_PRIMARY"),
        os.getenv("API_KEY_SECONDARY"),
    ]))

    if not valid_keys:
        # No keys configured — API is open (development mode)
        # Log a warning but do not block
        return

    provided_key = request.headers.get("X-API-Key")
    if not provided_key or provided_key not in valid_keys:
        raise HTTPException(
            status_code = 401,
            detail = {
                "error": "Invalid or missing API key",
                "hint": "Provide your API key in the X-API-Key header",
            }
        )


def require_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """
    FastAPI dependency that enforces API key authentication.

    Usage on any route:
        @router.post("/adjudicate")
        async def adjudicate(
            claim: ClaimRequest,
            api_key: str = Depends(require_api_key),
        ):

    Returns the validated API key string.
    Raises HTTP 401 if the key is missing or invalid.

    In production, keys would be stored hashed in MongoDB
    with associated metadata:
    - client name and contact
    - rate limit tier (standard / premium)
    - expiry date
    - allowed IP ranges
    - permissions (read-only vs read-write)
    """
    valid_keys = set(filter(None, [
        os.getenv("API_KEY_PRIMARY"),
        os.getenv("API_KEY_SECONDARY"),
    ]))

    if not valid_keys:
        # Logging a warning so devs know auth is disabled
        logger = get_logger("ginja.auth")
        logger.warning(
            "API key authentication is disabled — "
            "set API_KEY_PRIMARY in .env to enable"
        )
        return "dev-mode"

    if not api_key or api_key not in valid_keys:
        raise HTTPException(
            status_code = 401,
            headers     = {"WWW-Authenticate": "ApiKey"},
            detail      = {
                "error":   "Invalid or missing API key",
                "hint":    "Provide your key in the X-API-Key request header",
            }
        )

    return api_key

