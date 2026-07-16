from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .references import AndyThreadReference, validate_reference


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ThreadKind(str, Enum):
    DATA_QUALITY = "DATA_QUALITY"
    MEASUREMENT_GAP = "MEASUREMENT_GAP"
    CADENCE_ISSUE = "CADENCE_ISSUE"
    TERMINAL_MAPPING = "TERMINAL_MAPPING"
    VARIABLE_MAPPING = "VARIABLE_MAPPING"
    LOAD_FLOW_ANOMALY = "LOAD_FLOW_ANOMALY"
    POWER_INVERSION = "POWER_INVERSION"
    AT_BT_TRANSITION = "AT_BT_TRANSITION"
    SWITCHING_EVENT = "SWITCHING_EVENT"
    WORK_MAINTENANCE_IMPACT = "WORK_MAINTENANCE_IMPACT"
    PROTECTION_AUTOMATION_SIGNAL = "PROTECTION_AUTOMATION_SIGNAL"
    BI_DATASET_ISSUE = "BI_DATASET_ISSUE"
    ACCESS_RLS_ISSUE = "ACCESS_RLS_ISSUE"
    PARITY_DESKTOP_BI = "PARITY_DESKTOP_BI"
    GENERAL_REVIEW = "GENERAL_REVIEW"


class ThreadStatus(str, Enum):
    OPEN = "OPEN"
    TRIAGED = "TRIAGED"
    WAITING_DATA_OWNER = "WAITING_DATA_OWNER"
    WAITING_ENGINEERING = "WAITING_ENGINEERING"
    WAITING_OPERATION = "WAITING_OPERATION"
    WAITING_CADASTRE = "WAITING_CADASTRE"
    WAITING_MAINTENANCE = "WAITING_MAINTENANCE"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    RESOLVED = "RESOLVED"
    ARCHIVED = "ARCHIVED"


class DecisionType(str, Enum):
    MEASUREMENT_VALIDATED = "MEASUREMENT_VALIDATED"
    MEASUREMENT_SUSPECT = "MEASUREMENT_SUSPECT"
    CATALOG_ERROR = "CATALOG_ERROR"
    OPERATIONAL_EVENT = "OPERATIONAL_EVENT"
    SWITCHING_CONFIRMED = "SWITCHING_CONFIRMED"
    WORK_IMPACT_CONFIRMED = "WORK_IMPACT_CONFIRMED"
    LOAD_FLOW_ANOMALY_CONFIRMED = "LOAD_FLOW_ANOMALY_CONFIRMED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    NEEDS_FIELD_CHECK = "NEEDS_FIELD_CHECK"
    NEEDS_SOURCE_CORRECTION = "NEEDS_SOURCE_CORRECTION"


class MessageKind(str, Enum):
    COMMENT = "COMMENT"
    STATUS_CHANGE = "STATUS_CHANGE"
    DECISION = "DECISION"
    SYSTEM_EVENT = "SYSTEM_EVENT"


class ThreadPriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class ThreadParticipant:
    subject: str
    display_name: str = ""
    sector_id: str = ""
    roles: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.subject.strip():
            raise ValueError("participant_subject_required")


@dataclass
class ThreadMessage:
    message_id: str
    thread_id: str
    author: ThreadParticipant
    body: str
    message_kind: MessageKind = MessageKind.COMMENT
    created_at: str = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.message_kind = MessageKind(self.message_kind)
        if not self.thread_id.strip():
            raise ValueError("message_thread_id_required")
        if not self.message_id.strip():
            raise ValueError("message_id_required")


@dataclass
class DecisionRecord:
    decision_id: str
    thread_id: str
    decision_type: DecisionType
    summary: str
    decided_by: ThreadParticipant
    evidence_refs: tuple[str, ...]
    created_at: str = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.decision_type = DecisionType(self.decision_type)
        if not self.thread_id.strip():
            raise ValueError("decision_thread_id_required")
        if not self.decision_id.strip():
            raise ValueError("decision_id_required")
        if not self.evidence_refs:
            raise ValueError("decision_evidence_refs_required")


@dataclass
class ThreadAuditEvent:
    event_id: str
    thread_id: str
    event_type: str
    actor: str
    timestamp: str = field(default_factory=_utc_now)
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("audit_event_id_required")
        if not self.thread_id.strip():
            raise ValueError("audit_thread_id_required")
        if not self.event_type.strip():
            raise ValueError("audit_event_type_required")


@dataclass
class AndyThread:
    thread_id: str
    title: str
    kind: ThreadKind
    reference: AndyThreadReference
    created_by: ThreadParticipant
    status: ThreadStatus = ThreadStatus.OPEN
    priority: ThreadPriority = ThreadPriority.NORMAL
    owner_sector: str = ""
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)
    tags: tuple[str, ...] = field(default_factory=tuple)
    messages: list[ThreadMessage] = field(default_factory=list)
    decisions: list[DecisionRecord] = field(default_factory=list)
    resolved_reason: str | None = None

    def __post_init__(self) -> None:
        self.kind = ThreadKind(self.kind)
        self.status = ThreadStatus(self.status)
        self.priority = ThreadPriority(self.priority)
        if not self.thread_id.strip():
            raise ValueError("thread_id_required")
        if not self.title.strip():
            raise ValueError("thread_title_required")
        failures = validate_reference(self.reference)
        if failures:
            raise ValueError("thread_reference_invalid:" + ",".join(failures))
        if self.status == ThreadStatus.RESOLVED and not (self.decisions or self.resolved_reason):
            raise ValueError("resolved_thread_requires_decision_or_reason")


@dataclass(frozen=True)
class ThreadSummary:
    thread_id: str
    title: str
    kind: ThreadKind
    status: ThreadStatus
    priority: ThreadPriority
    owner_sector: str
    reference_key: str
    message_count: int = 0
    decision_count: int = 0
