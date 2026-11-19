import json
import logging
import sys
from datetime import datetime, timezone

from app.core.request_context import request_id_var

class JsonFormatter(logging.Formatter):
    """Turns each log record into one line of JSON."""


    def __init__(self,service_name: str) -> None:
        super().__init__()
        self.service_name = service_name


    def format(self, record: logging.LogRecord)-> str:
        log = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get()
        }

        fields = getattr(record, "fields", None)
        if fields:
            log.update(fields)

        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)

        return json.dumps(log, default=str)


def setup_logging(service_name: str, level: str)-> None:
    """Send all logs, including uvicorn's, to stdout as JSON."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service_name))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True    
    logging.getLogger("uvicorn.access").disabled = True