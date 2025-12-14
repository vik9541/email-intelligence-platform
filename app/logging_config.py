"""Structured logging configuration for ELK stack."""

import json
import logging
from datetime import datetime

from pythonjsonlogger import jsonlogger

# JSON logging for ELK
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)


def log_event(event_type: str, message: str, **kwargs):
    """Log structured events for ELK."""
    logger.info(
        json.dumps(
            {
                "event_type": event_type,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                **kwargs,
            }
        )
    )


# Usage examples:
# log_event("email_processed", "Email processed successfully",
#           email_id="123", duration_ms=150, status="success")
# log_event("error", "Failed to connect to database",
#           error_type="ConnectionError", retry_count=3)
