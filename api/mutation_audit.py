import json
import logging
import time
from datetime import datetime, timezone

from fastapi import Request


logger = logging.getLogger(__name__)


def log_mutation(
    request: Request,
    *,
    domain: str,
    resource_id: str,
    route: str,
    worksheets: tuple[str, ...],
    outcome: str,
    status_code: int,
    started_at: float,
) -> None:
    operation_id = request.state.operation_id
    event = {
        "duration_ms": round((time.perf_counter() - started_at) * 1000, 3),
        "event": f"nexo.{domain}.mutation",
        "operation_id": operation_id,
        "outcome": outcome,
        "request_id": operation_id,
        "resource_id": resource_id,
        "route": route,
        "status": status_code,
        "timestamp": datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
        "worksheets": list(worksheets),
    }
    level = (
        logging.WARNING
        if outcome == "conflict"
        else logging.ERROR
        if outcome == "failure"
        else logging.INFO
    )
    logger.log(level, json.dumps(event, ensure_ascii=False, sort_keys=True))
