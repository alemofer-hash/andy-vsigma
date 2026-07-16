from __future__ import annotations

import re
import uuid
from typing import Any, Mapping

from .models import ThreadAuditEvent, _utc_now


THREAD_AUDIT_EVENTS = {
    "THREAD_CREATED",
    "MESSAGE_ADDED",
    "STATUS_CHANGED",
    "DECISION_CREATED",
    "THREAD_EXPORTED",
    "ACCESS_DENIED",
    "POLICY_EVALUATED",
}

SENSITIVE_KEYS = ("password", "secret", "token", "credential", "private", "path")
UNC_PATTERN = re.compile(r"\\\\[^\\\s]+\\[^\s]+")
WINDOWS_USER_PATTERN = re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+\\[^\s]+")


def append_thread_audit_event(
    events: list[ThreadAuditEvent],
    *,
    thread_id: str,
    event_type: str,
    actor: str,
    payload: Mapping[str, Any] | None = None,
) -> ThreadAuditEvent:
    event = ThreadAuditEvent(
        event_id=str(uuid.uuid4()),
        thread_id=thread_id,
        event_type=event_type,
        actor=actor,
        timestamp=_utc_now(),
        payload=redact_audit_payload(dict(payload or {})),
    )
    events.append(event)
    return event


def audit_public_summary(events: list[ThreadAuditEvent]) -> dict[str, Any]:
    return {
        "event_count": len(events),
        "event_types": sorted({event.event_type for event in events}),
        "last_event_at": events[-1].timestamp if events else None,
    }


def redact_audit_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        lowered = key.lower()
        if any(marker in lowered for marker in SENSITIVE_KEYS):
            redacted[key] = "[REDACTED]"
        elif isinstance(value, Mapping):
            redacted[key] = redact_audit_payload(value)
        elif isinstance(value, str):
            redacted[key] = _redact_text(value)
        else:
            redacted[key] = value
    return redacted


def _redact_text(value: str) -> str:
    value = UNC_PATTERN.sub("[REDACTED_PATH]", value)
    value = WINDOWS_USER_PATTERN.sub("[REDACTED_PATH]", value)
    return value
