from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .audit import redact_audit_payload
from .feedback import HumanFeedbackCaptcha, TrainingLabel


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class EventCandidateType(str, Enum):
    POWER_INVERSION_CANDIDATE = "POWER_INVERSION_CANDIDATE"
    SWITCHING_CANDIDATE = "SWITCHING_CANDIDATE"
    CENTROID_DISPLACEMENT_ANOMALY = "CENTROID_DISPLACEMENT_ANOMALY"
    MULTI_FEEDER_CORRELATION_CONCEPT = "MULTI_FEEDER_CORRELATION_CONCEPT"
    ACTOR_CRITIC_CONCEPT = "ACTOR_CRITIC_CONCEPT"


class EventCandidateStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    HUMAN_REVIEWED = "HUMAN_REVIEWED"
    HUMAN_CONFIRMED = "HUMAN_CONFIRMED"
    SCADA_CONFIRMED = "SCADA_CONFIRMED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    INCONCLUSIVE = "INCONCLUSIVE"
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"


class EventEvidenceSource(str, Enum):
    ANDY_ENGINE = "ANDY_ENGINE"
    CENTROID_THRESHOLD = "CENTROID_THRESHOLD"
    HUMAN_FEEDBACK = "HUMAN_FEEDBACK"
    SCADA_LABEL = "SCADA_LABEL"
    MEASUREMENT_QUALITY = "MEASUREMENT_QUALITY"
    CADASTRE_REVIEW = "CADASTRE_REVIEW"
    OPERATIONAL_LOG = "OPERATIONAL_LOG"
    SYNTHETIC_CONCEPT = "SYNTHETIC_CONCEPT"


class EventValidationLevel(str, Enum):
    STATISTICAL_CANDIDATE = "STATISTICAL_CANDIDATE"
    HUMAN_CONFIRMED = "HUMAN_CONFIRMED"
    OPERATIONAL_SCADA_CONFIRMED = "OPERATIONAL_SCADA_CONFIRMED"
    CONCEPTUAL_ONLY = "CONCEPTUAL_ONLY"
    REJECTED = "REJECTED"


CONCEPTUAL_TYPES = {
    EventCandidateType.MULTI_FEEDER_CORRELATION_CONCEPT,
    EventCandidateType.ACTOR_CRITIC_CONCEPT,
}


@dataclass(frozen=True)
class EventCandidate:
    candidate_id: str
    occurrence_id: str
    thread_id: str
    reference_key: str
    candidate_type: EventCandidateType | str
    status: EventCandidateStatus | str
    validation_level: EventValidationLevel | str
    score: float
    evidence_sources: tuple[EventEvidenceSource | str, ...]
    generated_by: str = "andy.experimental.proposal_only"
    created_at: str = field(default_factory=_utc_now)
    model_version: str | None = None
    engine_version: str | None = None
    centroid_metrics: dict[str, Any] = field(default_factory=dict)
    feature_summary: dict[str, Any] = field(default_factory=dict)
    feedback_ids: tuple[str, ...] = ()
    decision_applied: bool = False
    notes_redacted: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_type", EventCandidateType(self.candidate_type))
        object.__setattr__(self, "status", EventCandidateStatus(self.status))
        object.__setattr__(self, "validation_level", EventValidationLevel(self.validation_level))
        object.__setattr__(
            self,
            "evidence_sources",
            tuple(EventEvidenceSource(source) for source in self.evidence_sources),
        )
        object.__setattr__(self, "centroid_metrics", redact_audit_payload(dict(self.centroid_metrics)))
        object.__setattr__(self, "feature_summary", redact_audit_payload(dict(self.feature_summary)))
        object.__setattr__(self, "metadata", redact_audit_payload(dict(self.metadata)))
        object.__setattr__(self, "feedback_ids", tuple(str(item) for item in self.feedback_ids))
        object.__setattr__(self, "notes_redacted", _redact_text(self.notes_redacted))
        self._validate()

    @property
    def is_operationally_confirmed(self) -> bool:
        return (
            self.status == EventCandidateStatus.SCADA_CONFIRMED
            and self.validation_level == EventValidationLevel.OPERATIONAL_SCADA_CONFIRMED
        )

    @property
    def is_conceptual_only(self) -> bool:
        return self.validation_level == EventValidationLevel.CONCEPTUAL_ONLY

    def _validate(self) -> None:
        required = {
            "candidate_id": self.candidate_id,
            "occurrence_id": self.occurrence_id,
            "thread_id": self.thread_id,
            "reference_key": self.reference_key,
            "created_at": self.created_at,
            "generated_by": self.generated_by,
        }
        for field_name, value in required.items():
            if not str(value or "").strip():
                raise ValueError(f"{field_name}_required")
        if not 0.0 <= float(self.score) <= 1.0:
            raise ValueError("candidate_score_out_of_range")
        if self.decision_applied:
            raise ValueError("event_candidate_cannot_apply_operational_decision")
        if not self.evidence_sources:
            raise ValueError("candidate_evidence_source_required")
        if self.candidate_type in CONCEPTUAL_TYPES:
            if self.validation_level != EventValidationLevel.CONCEPTUAL_ONLY:
                raise ValueError("conceptual_candidate_must_remain_conceptual")
            if self.status != EventCandidateStatus.QUARANTINED:
                raise ValueError("conceptual_candidate_must_be_quarantined")
        if self.status == EventCandidateStatus.SCADA_CONFIRMED:
            if EventEvidenceSource.SCADA_LABEL not in self.evidence_sources:
                raise ValueError("scada_confirmed_candidate_requires_scada_label")
            if self.validation_level != EventValidationLevel.OPERATIONAL_SCADA_CONFIRMED:
                raise ValueError("scada_confirmed_candidate_requires_operational_validation")
        if self.validation_level == EventValidationLevel.OPERATIONAL_SCADA_CONFIRMED:
            if EventEvidenceSource.SCADA_LABEL not in self.evidence_sources:
                raise ValueError("operational_validation_requires_scada_label")
            if self.status != EventCandidateStatus.SCADA_CONFIRMED:
                raise ValueError("operational_validation_requires_scada_status")


def create_centroid_candidate(
    *,
    candidate_id: str,
    occurrence_id: str,
    thread_id: str,
    reference_key: str,
    score: float,
    centroid_metrics: dict[str, Any],
    model_version: str | None = "centroid-theorem-proposal-v0",
    engine_version: str | None = None,
    notes_redacted: str = "",
    metadata: dict[str, Any] | None = None,
) -> EventCandidate:
    return EventCandidate(
        candidate_id=candidate_id,
        occurrence_id=occurrence_id,
        thread_id=thread_id,
        reference_key=reference_key,
        candidate_type=EventCandidateType.CENTROID_DISPLACEMENT_ANOMALY,
        status=EventCandidateStatus.CANDIDATE,
        validation_level=EventValidationLevel.STATISTICAL_CANDIDATE,
        score=score,
        evidence_sources=(EventEvidenceSource.ANDY_ENGINE, EventEvidenceSource.CENTROID_THRESHOLD),
        model_version=model_version,
        engine_version=engine_version,
        centroid_metrics=centroid_metrics,
        notes_redacted=notes_redacted,
        metadata=metadata or {},
    )


def create_power_inversion_candidate(
    *,
    candidate_id: str,
    occurrence_id: str,
    thread_id: str,
    reference_key: str,
    score: float,
    feature_summary: dict[str, Any],
    model_version: str | None = "andy-flow-proposal-v0",
    engine_version: str | None = None,
    notes_redacted: str = "",
    metadata: dict[str, Any] | None = None,
) -> EventCandidate:
    return EventCandidate(
        candidate_id=candidate_id,
        occurrence_id=occurrence_id,
        thread_id=thread_id,
        reference_key=reference_key,
        candidate_type=EventCandidateType.POWER_INVERSION_CANDIDATE,
        status=EventCandidateStatus.CANDIDATE,
        validation_level=EventValidationLevel.STATISTICAL_CANDIDATE,
        score=score,
        evidence_sources=(EventEvidenceSource.ANDY_ENGINE,),
        model_version=model_version,
        engine_version=engine_version,
        feature_summary=feature_summary,
        notes_redacted=notes_redacted,
        metadata=metadata or {},
    )


def create_conceptual_actor_critic_candidate(
    *,
    candidate_id: str,
    occurrence_id: str,
    thread_id: str,
    reference_key: str,
    feature_summary: dict[str, Any] | None = None,
    notes_redacted: str = "",
) -> EventCandidate:
    return EventCandidate(
        candidate_id=candidate_id,
        occurrence_id=occurrence_id,
        thread_id=thread_id,
        reference_key=reference_key,
        candidate_type=EventCandidateType.ACTOR_CRITIC_CONCEPT,
        status=EventCandidateStatus.QUARANTINED,
        validation_level=EventValidationLevel.CONCEPTUAL_ONLY,
        score=0.0,
        evidence_sources=(EventEvidenceSource.SYNTHETIC_CONCEPT,),
        model_version="actor-critic-concept-v0",
        feature_summary=feature_summary or {},
        notes_redacted=notes_redacted,
    )


def apply_feedback_to_candidate(candidate: EventCandidate, feedback: HumanFeedbackCaptcha) -> EventCandidate:
    if candidate.reference_key != feedback.reference_key:
        raise ValueError("feedback_reference_mismatch")
    if candidate.occurrence_id != feedback.occurrence_id:
        raise ValueError("feedback_occurrence_mismatch")
    if candidate.thread_id != feedback.thread_id:
        raise ValueError("feedback_thread_mismatch")
    if candidate.candidate_type in CONCEPTUAL_TYPES:
        raise ValueError("conceptual_candidate_cannot_be_promoted_by_feedback")

    evidence_sources = _append_unique(candidate.evidence_sources, EventEvidenceSource.HUMAN_FEEDBACK)
    status = EventCandidateStatus.HUMAN_REVIEWED
    validation_level = candidate.validation_level

    if feedback.training_label == TrainingLabel.POSITIVE_SCADA_CONFIRMED:
        evidence_sources = _append_unique(evidence_sources, EventEvidenceSource.SCADA_LABEL)
        status = EventCandidateStatus.SCADA_CONFIRMED
        validation_level = EventValidationLevel.OPERATIONAL_SCADA_CONFIRMED
    elif feedback.training_label == TrainingLabel.POSITIVE_HUMAN_CONFIRMED:
        status = EventCandidateStatus.HUMAN_CONFIRMED
        validation_level = EventValidationLevel.HUMAN_CONFIRMED
    elif feedback.training_label == TrainingLabel.NEGATIVE_FALSE_POSITIVE:
        status = EventCandidateStatus.FALSE_POSITIVE
        validation_level = EventValidationLevel.REJECTED
    elif feedback.training_label in {
        TrainingLabel.PARTIAL_INCOMPLETE,
        TrainingLabel.UNKNOWN_INCONCLUSIVE,
        TrainingLabel.UNKNOWN_NO_EVIDENCE,
    }:
        status = EventCandidateStatus.INCONCLUSIVE
        validation_level = EventValidationLevel.STATISTICAL_CANDIDATE

    return replace(
        candidate,
        status=status,
        validation_level=validation_level,
        evidence_sources=evidence_sources,
        feedback_ids=tuple(dict.fromkeys((*candidate.feedback_ids, feedback.feedback_id))),
    )


def candidate_to_dict(candidate: EventCandidate) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "occurrence_id": candidate.occurrence_id,
        "thread_id": candidate.thread_id,
        "reference_key": candidate.reference_key,
        "candidate_type": candidate.candidate_type.value,
        "status": candidate.status.value,
        "validation_level": candidate.validation_level.value,
        "score": float(candidate.score),
        "evidence_sources": [source.value for source in candidate.evidence_sources],
        "generated_by": candidate.generated_by,
        "created_at": candidate.created_at,
        "model_version": candidate.model_version,
        "engine_version": candidate.engine_version,
        "centroid_metrics": candidate.centroid_metrics,
        "feature_summary": candidate.feature_summary,
        "feedback_ids": list(candidate.feedback_ids),
        "decision_applied": candidate.decision_applied,
        "notes_redacted": candidate.notes_redacted,
        "metadata": candidate.metadata,
        "operationally_confirmed": candidate.is_operationally_confirmed,
        "conceptual_only": candidate.is_conceptual_only,
    }


def candidate_from_dict(payload: dict[str, Any]) -> EventCandidate:
    return EventCandidate(
        candidate_id=str(payload["candidate_id"]),
        occurrence_id=str(payload["occurrence_id"]),
        thread_id=str(payload["thread_id"]),
        reference_key=str(payload["reference_key"]),
        candidate_type=str(payload["candidate_type"]),
        status=str(payload["status"]),
        validation_level=str(payload["validation_level"]),
        score=float(payload["score"]),
        evidence_sources=tuple(payload["evidence_sources"]),
        generated_by=str(payload.get("generated_by") or "andy.experimental.proposal_only"),
        created_at=str(payload["created_at"]),
        model_version=payload.get("model_version"),
        engine_version=payload.get("engine_version"),
        centroid_metrics=dict(payload.get("centroid_metrics") or {}),
        feature_summary=dict(payload.get("feature_summary") or {}),
        feedback_ids=tuple(payload.get("feedback_ids") or ()),
        decision_applied=bool(payload.get("decision_applied", False)),
        notes_redacted=str(payload.get("notes_redacted") or ""),
        metadata=dict(payload.get("metadata") or {}),
    )


def export_event_candidate_dataset(candidates: list[EventCandidate]) -> list[dict[str, Any]]:
    return [candidate_to_dict(item) for item in candidates]


def _append_unique(
    values: tuple[EventEvidenceSource | str, ...],
    new_value: EventEvidenceSource,
) -> tuple[EventEvidenceSource, ...]:
    normalized = [EventEvidenceSource(item) for item in values]
    if new_value not in normalized:
        normalized.append(new_value)
    return tuple(normalized)


def _redact_text(value: str) -> str:
    return str(redact_audit_payload({"value": value}).get("value", ""))
