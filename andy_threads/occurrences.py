from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .models import ThreadParticipant
from .references import AndyThreadReference, reference_key, validate_reference
from .sector_lens import SectorId


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class OccurrenceStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    FORWARDED = "FORWARDED"
    WAITING_HUMAN_FEEDBACK = "WAITING_HUMAN_FEEDBACK"
    WAITING_OTHER_SECTOR = "WAITING_OTHER_SECTOR"
    FINALIZED = "FINALIZED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


class OccurrenceSeverity(str, Enum):
    S0_OBSERVATION = "S0_OBSERVATION"
    S1_PRODUCTIVITY_BLOCKER = "S1_PRODUCTIVITY_BLOCKER"
    S2_ENGINEERING_BLOCKER = "S2_ENGINEERING_BLOCKER"
    S3_OPERATIONAL_RISK = "S3_OPERATIONAL_RISK"
    S4_CRITICAL_DECISION_RISK = "S4_CRITICAL_DECISION_RISK"


class OccurrenceDomain(str, Enum):
    ELECTRICAL_PARAMETER = "ELECTRICAL_PARAMETER"
    POWER_INVERSION = "POWER_INVERSION"
    SWITCHING_EVENT = "SWITCHING_EVENT"
    MEASUREMENT_AVAILABILITY = "MEASUREMENT_AVAILABILITY"
    CADASTRE_MAPPING = "CADASTRE_MAPPING"
    ANALYTIC_DIVERGENCE = "ANALYTIC_DIVERGENCE"
    EXPORT_DASHBOARD = "EXPORT_DASHBOARD"
    BI_ACCESS = "BI_ACCESS"
    TOOL_RUNTIME = "TOOL_RUNTIME"


class FeedbackStatus(str, Enum):
    NOT_REQUESTED = "NOT_REQUESTED"
    REQUESTED = "REQUESTED"
    RECEIVED = "RECEIVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


TERMINAL_OCCURRENCE_STATUSES = {
    OccurrenceStatus.FINALIZED,
    OccurrenceStatus.REJECTED,
    OccurrenceStatus.ARCHIVED,
}


HIGH_RISK_SEVERITIES = {
    OccurrenceSeverity.S3_OPERATIONAL_RISK,
    OccurrenceSeverity.S4_CRITICAL_DECISION_RISK,
}


@dataclass(frozen=True)
class Occurrence:
    occurrence_id: str
    thread_id: str
    title: str
    summary: str
    problem_domain: OccurrenceDomain | str
    reference: AndyThreadReference
    owner_sector: SectorId | str
    created_by: ThreadParticipant
    status: OccurrenceStatus | str = OccurrenceStatus.OPEN
    severity: OccurrenceSeverity | str = OccurrenceSeverity.S1_PRODUCTIVITY_BLOCKER
    target_sector: SectorId | str | None = None
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)
    closed_at: str | None = None
    closure_reason: str | None = None
    feedback_status: FeedbackStatus | str = FeedbackStatus.NOT_REQUESTED
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    decision_refs: tuple[str, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", OccurrenceStatus(self.status))
        object.__setattr__(self, "severity", OccurrenceSeverity(self.severity))
        object.__setattr__(self, "problem_domain", OccurrenceDomain(self.problem_domain))
        object.__setattr__(self, "owner_sector", SectorId(self.owner_sector))
        object.__setattr__(self, "feedback_status", FeedbackStatus(self.feedback_status))
        if self.target_sector is not None:
            object.__setattr__(self, "target_sector", SectorId(self.target_sector))
        self._validate()

    @property
    def reference_key(self) -> str:
        return reference_key(self.reference)

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_OCCURRENCE_STATUSES

    @property
    def requires_evidence_or_decision_to_close(self) -> bool:
        return self.severity in HIGH_RISK_SEVERITIES

    def transition(
        self,
        status: OccurrenceStatus | str,
        *,
        actor: ThreadParticipant,
        target_sector: SectorId | str | None = None,
        closure_reason: str | None = None,
        evidence_refs: tuple[str, ...] | None = None,
        decision_refs: tuple[str, ...] | None = None,
    ) -> "Occurrence":
        if not actor.subject.strip():
            raise ValueError("occurrence_transition_actor_required")
        active_status = OccurrenceStatus(status)
        active_evidence = tuple(evidence_refs if evidence_refs is not None else self.evidence_refs)
        active_decisions = tuple(decision_refs if decision_refs is not None else self.decision_refs)
        active_target = target_sector if target_sector is not None else self.target_sector
        active_closure_reason = closure_reason if closure_reason is not None else self.closure_reason
        return replace(
            self,
            status=active_status,
            target_sector=active_target,
            updated_at=_utc_now(),
            closed_at=_utc_now() if active_status in TERMINAL_OCCURRENCE_STATUSES else None,
            closure_reason=active_closure_reason,
            evidence_refs=active_evidence,
            decision_refs=active_decisions,
        )

    def _validate(self) -> None:
        if not self.occurrence_id.strip():
            raise ValueError("occurrence_id_required")
        if not self.thread_id.strip():
            raise ValueError("occurrence_thread_id_required")
        if not self.title.strip():
            raise ValueError("occurrence_title_required")
        if not self.summary.strip():
            raise ValueError("occurrence_summary_required")
        if not isinstance(self.reference, AndyThreadReference):
            raise ValueError("occurrence_reference_required")
        failures = validate_reference(self.reference)
        if failures:
            raise ValueError("occurrence_reference_invalid:" + ",".join(failures))
        if self.status in {OccurrenceStatus.FORWARDED, OccurrenceStatus.WAITING_OTHER_SECTOR} and self.target_sector is None:
            raise ValueError("forwarded_occurrence_requires_target_sector")
        if self.status in TERMINAL_OCCURRENCE_STATUSES and not _has_text(self.closure_reason):
            raise ValueError("terminal_occurrence_requires_closure_reason")
        if (
            self.status in TERMINAL_OCCURRENCE_STATUSES
            and self.severity in HIGH_RISK_SEVERITIES
            and not (self.evidence_refs or self.decision_refs)
        ):
            raise ValueError("high_risk_occurrence_requires_evidence_or_decision_before_closure")
        if self.closed_at and self.status not in TERMINAL_OCCURRENCE_STATUSES:
            raise ValueError("closed_at_requires_terminal_status")


def create_occurrence(
    *,
    occurrence_id: str,
    thread_id: str,
    title: str,
    summary: str,
    problem_domain: OccurrenceDomain | str,
    reference: AndyThreadReference,
    owner_sector: SectorId | str,
    created_by: ThreadParticipant,
    severity: OccurrenceSeverity | str = OccurrenceSeverity.S1_PRODUCTIVITY_BLOCKER,
    target_sector: SectorId | str | None = None,
    tags: tuple[str, ...] = (),
    metadata: dict[str, Any] | None = None,
) -> Occurrence:
    return Occurrence(
        occurrence_id=occurrence_id,
        thread_id=thread_id,
        title=title,
        summary=summary,
        problem_domain=problem_domain,
        reference=reference,
        owner_sector=owner_sector,
        created_by=created_by,
        severity=severity,
        target_sector=target_sector,
        tags=tuple(tags),
        metadata=dict(metadata or {}),
    )


def occurrence_public_summary(occurrence: Occurrence) -> dict[str, Any]:
    return {
        "occurrence_id": occurrence.occurrence_id,
        "thread_id": occurrence.thread_id,
        "title": occurrence.title,
        "status": occurrence.status.value,
        "severity": occurrence.severity.value,
        "problem_domain": occurrence.problem_domain.value,
        "reference_key": occurrence.reference_key,
        "owner_sector": occurrence.owner_sector.value,
        "target_sector": occurrence.target_sector.value if occurrence.target_sector is not None else None,
        "feedback_status": occurrence.feedback_status.value,
        "evidence_count": len(occurrence.evidence_refs),
        "decision_count": len(occurrence.decision_refs),
        "created_at": occurrence.created_at,
        "updated_at": occurrence.updated_at,
        "closed_at": occurrence.closed_at,
    }


def _has_text(value: Any) -> bool:
    return value is not None and str(value).strip() != ""
