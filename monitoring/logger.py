"""
Structured Logging
All log output uses JSON format with consistent fields.
This makes logs parseable by aggregation tools like
Datadog, ELK Stack, or Google Cloud Logging.

Every log line includes:
- timestamp
- level
- logger name
- message
- any extra fields passed to the logger

Usage:
    from monitoring.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Claim adjudicated", extra={"claim_id": "CLM-001", "decision": "Pass"})
"""

import json
import logging
import sys
from datetime import datetime, timezone


class StructuredFormatter(logging.Formatter):
    """
    Formats log records as JSON objects.
    One JSON object per line — compatible with
    all major log aggregation platforms.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_object = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include any extra fields passed to the logger
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "levelname", "levelno",
                "pathname", "filename", "module", "exc_info",
                "exc_text", "stack_info", "lineno", "funcName",
                "created", "msecs", "relativeCreated", "thread",
                "threadName", "processName", "process", "message",
                "taskName",
            ):
                log_object[key] = value

        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_object)


def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger configured with structured JSON output.
    Call once per module with __name__ as the argument.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(
            getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
        )
        logger.propagate = False

    return logger


import os


def log_adjudication(result: dict) -> None:
    """
    Logs a completed adjudication decision with all relevant fields.
    """
    logger = get_logger("ginja.adjudication")
    logger.info(
        "Adjudication complete",
        extra={
            "claim_id": result.get("claim_id"),
            "decision": result.get("decision"),
            "risk_score": result.get("risk_score"),
            "confidence": result.get("confidence"),
            "stage": result.get("adjudication_stage"),
            "processing_ms": result.get("processing_time_ms"),
        }
    )