import json
import logging
from datetime import datetime

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("ginja.claims")

def log_adjudication(result: dict) -> None:
    """
    Logs a structured record of every adjudication decision.
    """
    logger.info(json.dumps({
        "event": "adjudication_complete",
        "claim_id": result.get("claim_id"),
        "decision": result.get("decision"),
        "risk_score": result.get("risk_score"),
        "confidence": result.get("confidence"),
        "stage": result.get("adjudication_stage"),
        "processing_ms": result.get("processing_time_ms"),
        "timestamp": datetime.utcnow().isoformat(),
    }))
