from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from .audit import audit_public_summary
from .models import AndyThread, DecisionRecord, ThreadAuditEvent
from .references import reference_key, reference_public_summary


def thread_to_dict(thread: AndyThread, audit_events: list[ThreadAuditEvent] | None = None) -> dict[str, Any]:
    payload = _to_jsonable(thread)
    payload["reference"] = reference_public_summary(thread.reference)
    payload["reference_key"] = reference_key(thread.reference)
    payload["audit_summary"] = audit_public_summary(audit_events or [])
    payload["mvp_notice"] = "ANDY Threads local MVP; no attachments, no DM, no real identity provider."
    return payload


def thread_to_markdown(thread: AndyThread, audit_events: list[ThreadAuditEvent] | None = None) -> str:
    lines = [
        f"# {thread.title}",
        "",
        f"- Thread ID: `{thread.thread_id}`",
        f"- Status: `{thread.status.value}`",
        f"- Kind: `{thread.kind.value}`",
        f"- Priority: `{thread.priority.value}`",
        f"- Owner sector: `{thread.owner_sector}`",
        f"- Reference: `{reference_key(thread.reference)}`",
        "",
        "## Technical Reference",
    ]
    for key, value in reference_public_summary(thread.reference).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Messages"])
    if thread.messages:
        for message in thread.messages:
            lines.append(f"- `{message.created_at}` `{message.message_kind.value}` {message.author.subject}: {message.body}")
    else:
        lines.append("- No messages.")
    lines.extend(["", "## Decisions"])
    if thread.decisions:
        for decision in thread.decisions:
            lines.append(decision_to_markdown(decision))
    else:
        lines.append("- No decisions.")
    lines.extend(["", "## Audit Summary"])
    for key, value in audit_public_summary(audit_events or []).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "> ANDY Threads MVP local: no attachments, no DM, no real identity provider."])
    return "\n".join(lines) + "\n"


def decision_to_markdown(decision: DecisionRecord) -> str:
    evidence = ", ".join(f"`{item}`" for item in decision.evidence_refs)
    return f"- `{decision.created_at}` `{decision.decision_type.value}` {decision.summary} Evidence: {evidence}"


def reference_to_markdown(reference: Any) -> str:
    lines = ["## Reference"]
    for key, value in reference_public_summary(reference).items():
        lines.append(f"- {key}: `{value}`")
    return "\n".join(lines) + "\n"


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    return value
