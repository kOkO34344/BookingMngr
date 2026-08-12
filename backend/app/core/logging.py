"""Logging setup plus the domain-event helper used for the future audit trail.

Every meaningful state change (reservation status, task completion, unit
housekeeping status) goes through `log_event`, which writes both a structured
log line and an `audit_log` row. When a real audit UI is needed, the data is
already there.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger("bookingmngr")


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
    )


def log_event(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    action: str,
    actor: str | None = None,
    changes: dict[str, Any] | None = None,
    organization_id: int | None = None,
) -> None:
    """Record a domain event. Never raises — auditing must not break a request."""
    from app.models.audit import AuditLog  # local import avoids a cycle

    payload = _jsonable(changes or {})
    logger.info(
        "%s#%s %s by=%s changes=%s",
        entity_type,
        entity_id,
        action,
        actor or "system",
        json.dumps(payload, default=str),
    )
    try:
        db.add(
            AuditLog(
                organization_id=organization_id,
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                actor=actor,
                changes=payload,
            )
        )
        db.flush()
    except Exception:  # pragma: no cover - auditing is best-effort
        logger.exception("Failed to persist audit log for %s#%s", entity_type, entity_id)


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if hasattr(value, "value"):  # Enum
        return value.value
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def diff_fields(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Return {field: {"from": x, "to": y}} for changed keys only."""
    out: dict[str, Any] = {}
    for key, new in after.items():
        old = before.get(key)
        if old != new:
            out[key] = {"from": old, "to": new}
    return out
