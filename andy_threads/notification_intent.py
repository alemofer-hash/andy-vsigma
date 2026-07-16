from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .audit import redact_audit_payload
from .occurrences import Occurrence
from .sector_lens import SectorId


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class NotificationChannel(str, Enum):
    MANUAL_EMAIL = "MANUAL_EMAIL"
    MANUAL_TEAMS = "MANUAL_TEAMS"
    SECTOR_QUEUE = "SECTOR_QUEUE"
    TICKET_DRAFT = "TICKET_DRAFT"


class NotificationIntentStatus(str, Enum):
    DRAFT = "DRAFT"
    READY_FOR_HUMAN_SEND = "READY_FOR_HUMAN_SEND"
    SENT_EXTERNALLY_BY_HUMAN = "SENT_EXTERNALLY_BY_HUMAN"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class NotificationIntent:
    intent_id: str
    occurrence_id: str
    target_sector: SectorId | str
    target_channel: NotificationChannel | str
    subject: str
    body_redacted: str
    reference_key: str
    created_by: str
    status: NotificationIntentStatus | str = NotificationIntentStatus.DRAFT
    created_at: str = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_sector", SectorId(self.target_sector))
        object.__setattr__(self, "target_channel", NotificationChannel(self.target_channel))
        object.__setattr__(self, "status", NotificationIntentStatus(self.status))
        object.__setattr__(self, "subject", _redact_text(self.subject).strip())
        object.__setattr__(self, "body_redacted", _redact_text(self.body_redacted).strip())
        self._validate()

    def mark_ready_for_human_send(self) -> "NotificationIntent":
        return replace(self, status=NotificationIntentStatus.READY_FOR_HUMAN_SEND)

    def mark_sent_externally_by_human(self) -> "NotificationIntent":
        return replace(self, status=NotificationIntentStatus.SENT_EXTERNALLY_BY_HUMAN)

    def cancel(self) -> "NotificationIntent":
        return replace(self, status=NotificationIntentStatus.CANCELLED)

    def _validate(self) -> None:
        if not self.intent_id.strip():
            raise ValueError("notification_intent_id_required")
        if not self.occurrence_id.strip():
            raise ValueError("notification_occurrence_id_required")
        if not self.subject.strip():
            raise ValueError("notification_subject_required")
        if not self.body_redacted.strip():
            raise ValueError("notification_body_required")
        if not self.reference_key.strip():
            raise ValueError("notification_reference_key_required")
        if not self.created_by.strip():
            raise ValueError("notification_created_by_required")


def build_notification_intent(
    *,
    intent_id: str,
    occurrence: Occurrence,
    target_channel: NotificationChannel | str = NotificationChannel.MANUAL_EMAIL,
    created_by: str,
    status: NotificationIntentStatus | str = NotificationIntentStatus.DRAFT,
) -> NotificationIntent:
    target_sector = occurrence.target_sector or occurrence.owner_sector
    subject = f"[ANDY] Ocorrencia {occurrence.severity.value}: {occurrence.title}"
    body = "\n".join(
        [
            "Ocorrencia tecnica ANDY pronta para revisao humana.",
            "",
            f"Occurrence ID: {occurrence.occurrence_id}",
            f"Status: {occurrence.status.value}",
            f"Dominio: {occurrence.problem_domain.value}",
            f"Severidade: {occurrence.severity.value}",
            f"Setor destino: {target_sector.value}",
            f"Referencia: {occurrence.reference_key}",
            "",
            "Resumo redigido:",
            occurrence.summary,
            "",
            "Observacao: este intent nao envia e-mail/Teams automaticamente.",
        ]
    )
    return NotificationIntent(
        intent_id=intent_id,
        occurrence_id=occurrence.occurrence_id,
        target_sector=target_sector,
        target_channel=target_channel,
        subject=subject,
        body_redacted=body,
        reference_key=occurrence.reference_key,
        created_by=created_by,
        status=status,
    )


def notification_intent_to_dict(intent: NotificationIntent) -> dict[str, Any]:
    return {
        "intent_id": intent.intent_id,
        "occurrence_id": intent.occurrence_id,
        "target_sector": intent.target_sector.value,
        "target_channel": intent.target_channel.value,
        "subject": intent.subject,
        "body_redacted": intent.body_redacted,
        "reference_key": intent.reference_key,
        "created_by": intent.created_by,
        "status": intent.status.value,
        "created_at": intent.created_at,
        "metadata": redact_audit_payload(intent.metadata),
        "real_provider_enabled": False,
    }


def notification_intent_from_dict(payload: dict[str, Any]) -> NotificationIntent:
    return NotificationIntent(
        intent_id=str(payload["intent_id"]),
        occurrence_id=str(payload["occurrence_id"]),
        target_sector=str(payload["target_sector"]),
        target_channel=str(payload["target_channel"]),
        subject=str(payload["subject"]),
        body_redacted=str(payload["body_redacted"]),
        reference_key=str(payload["reference_key"]),
        created_by=str(payload["created_by"]),
        status=str(payload["status"]),
        created_at=str(payload["created_at"]),
        metadata=dict(payload.get("metadata") or {}),
    )


def _redact_text(value: str) -> str:
    return str(redact_audit_payload({"value": value}).get("value", ""))
