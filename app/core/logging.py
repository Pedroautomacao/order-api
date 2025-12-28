import logging
import sys
import json
from datetime import datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Extras opcionais
        for key in (
            "correlation_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "user_id",
            "snapshot_id",
        ):
            if hasattr(record, key):
                log_record[key] = getattr(record, key)

        if record.exc_info:
            log_record["exception"] = self.formatException(
                record.exc_info
            )

        return json.dumps(log_record)


logger = logging.getLogger("order_api")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

logger.propagate = False
