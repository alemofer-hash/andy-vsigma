from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .audit import redact_audit_payload
from .sector_lens import SectorId


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class FeedbackEventType(str, Enum):
    POWER_INVERSION = "POWER_INVERSION"
    SWITCHING_EVENT = "SWITCHING_EVENT"
    LOAD_FLOW_ANOMALY = "LOAD_FLOW_ANOMALY"
    MEASUREMENT_GAP = "MEASUREMENT_GAP"
    MEASUREMENT_SUSPECT = "MEASUREMENT_SUSPECT"
    CADASTRE_MAPPING = "CADASTRE_MAPPING"
    EXPORT_DASHBOARD = "EXPORT_DASHBOARD"
    BI_DATASET = "BI_DATASET"
    TOOL_RUNTIME = "TOOL_RUNTIME"
    INCONCLUSIVE = "INCONCLUSIVE"


class HumanVerdict(str, Enum):
    CORRECT = "CORRECT"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    INCOMPLETE = "INCOMPLETE"
    INCONCLUSIVE = "INCONCLUSIVE"
    NEEDS_OTHER_SECTOR = "NEEDS_OTHER_SECTOR"
    NOT_ENOUGH_EVIDENCE = "NOT_ENOUGH_EVIDENCE"


class FeedbackReasonCode(str, Enum):
    SCADA_CONFIRMS = "SCADA_CONFIRMS"
    SCADA_DOES_NOT_CONFIRM = "SCADA_DOES_NOT_CONFIRM"
    MEASUREMENT_BAD_QUALITY = "MEASUREMENT_BAD_QUALITY"
    MISSING_MEASUREMENT = "MISSING_MEASUREMENT"
    CADASTRE_MISMATCH = "CADASTRE_MISMATCH"
    PLANNED_WORK = "PLANNED_WORK"
    OPERATIONAL_SWITCHING = "OPERATIONAL_SWITCHING"
    LOAD_BEHAVIOR_EXPECTED = "LOAD_BEHAVIOR_EXPECTED"
    EXPORT_OR_QUERY_ERROR = "EXPORT_OR_QUERY_ERROR"
    NO_EVIDENCE = "NO_EVIDENCE"
    OTHER = "OTHER"


class TrainingLabel(str, Enum):
    POSITIVE_SCADA_CONFIRMED = "positive_scada_confirmed"
    POSITIVE_HUMAN_CONFIRMED = "positive_human_confirmed"
    NEGATIVE_FALSE_POSITIVE = "negative_false_positive"
    PARTIAL_INCOMPLETE = "partial_incomplete"
    UNKNOWN_INCONCLUSIVE = "unknown_inconclusive"
    ROUTED_NEEDS_SECTOR = "routed_needs_sector"
    UNKNOWN_NO_EVIDENCE = "unknown_no_evidence"


SCADA_CONFIRMED_REASON = FeedbackReasonCode.SCADA_CONFIRMS


@dataclass(frozen=True)
class HumanFeedbackCaptcha:
    feedback_id: str
    analysis_id: str
    occurrence_id: str
    thread_id: str
    reference_key: str
    event_type: FeedbackEventType | str
    human_verdict: HumanVerdict | str
    confidence_human: float
    reason_code: FeedbackReasonCode | str
    target_sector: SectorId | str
    evidence_ref: str
    reviewer_subject: str
    reviewer_sector: SectorId | str
    created_at: str = field(default_factory=_utc_now)
    training_label: TrainingLabel | str | None = None
    model_version: str | None = None
    engine_version: str | None = None
    notes_redacted: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", FeedbackEventType(self.event_type))
        object.__setattr__(self, "human_verdict", HumanVerdict(self.human_verdict))
        object.__setattr__(self, "reason_code", FeedbackReasonCode(self.reason_code))
        object.__setattr__(self, "target_sector", SectorId(self.target_sector))
        object.__setattr__(self, "reviewer_sector", SectorId(self.reviewer_sector))
        label = TrainingLabel(self.training_label) if self.training_label is not None else derive_training_label(
            self.event_type,
            self.human_verdict,
            self.reason_code,
        )
        object.__setattr__(self, "training_label", label)
        object.__setattr__(self, "notes_redacted", _redact_text(self.notes_redacted))
        object.__setattr__(self, "metadata", redact_audit_payload(dict(self.metadata)))
        self._validate()

    @property
    def is_positive_training_label(self) -> bool:
        return self.training_label in {
            TrainingLabel.POSITIVE_SCADA_CONFIRMED,
            TrainingLabel.POSITIVE_HUMAN_CONFIRMED,
        }

    @property
    def is_operationally_confirmed(self) -> bool:
        return self.training_label == TrainingLabel.POSITIVE_SCADA_CONFIRMED

    def _validate(self) -> None:
        required = {
            "feedback_id": self.feedback_id,
            "analysis_id": self.analysis_id,
            "occurrence_id": self.occurrence_id,
            "thread_id": self.thread_id,
            "reference_key": self.reference_key,
            "evidence_ref": self.evidence_ref,
            "reviewer_subject": self.reviewer_subject,
            "created_at": self.created_at,
        }
        for field_name, value in required.items():
            if not str(value or "").strip():
                raise ValueError(f"{field_name}_required")
        if not 0.0 <= float(self.confidence_human) <= 1.0:
            raise ValueError("confidence_human_out_of_range")
        if self.human_verdict in {HumanVerdict.FALSE_POSITIVE, HumanVerdict.INCONCLUSIVE, HumanVerdict.NOT_ENOUGH_EVIDENCE}:
            if self.is_positive_training_label:
                raise ValueError("non_positive_verdict_cannot_have_positive_training_label")
        if self.event_type == FeedbackEventType.SWITCHING_EVENT:
            if self.training_label == TrainingLabel.POSITIVE_SCADA_CONFIRMED and self.reason_code != FeedbackReasonCode.SCADA_CONFIRMS:
                raise ValueError("switching_event_scada_confirmation_requires_scada_reason")
        if self.reason_code == FeedbackReasonCode.SCADA_DOES_NOT_CONFIRM and self.is_positive_training_label:
            raise ValueError("scada_negative_reason_cannot_have_positive_training_label")


def derive_training_label(
    event_type: FeedbackEventType | str,
    human_verdict: HumanVerdict | str,
    reason_code: FeedbackReasonCode | str,
) -> TrainingLabel:
    active_event = FeedbackEventType(event_type)
    verdict = HumanVerdict(human_verdict)
    reason = FeedbackReasonCode(reason_code)
    if verdict == HumanVerdict.FALSE_POSITIVE:
        return TrainingLabel.NEGATIVE_FALSE_POSITIVE
    if verdict == HumanVerdict.INCOMPLETE:
        return TrainingLabel.PARTIAL_INCOMPLETE
    if verdict == HumanVerdict.INCONCLUSIVE:
        return TrainingLabel.UNKNOWN_INCONCLUSIVE
    if verdict == HumanVerdict.NEEDS_OTHER_SECTOR:
        return TrainingLabel.ROUTED_NEEDS_SECTOR
    if verdict == HumanVerdict.NOT_ENOUGH_EVIDENCE:
        return TrainingLabel.UNKNOWN_NO_EVIDENCE
    if verdict == HumanVerdict.CORRECT and reason == FeedbackReasonCode.SCADA_CONFIRMS:
        return TrainingLabel.POSITIVE_SCADA_CONFIRMED
    if active_event == FeedbackEventType.SWITCHING_EVENT and verdict == HumanVerdict.CORRECT:
        # A switching candidate without SCADA is useful supervision, not operational confirmation.
        return TrainingLabel.POSITIVE_HUMAN_CONFIRMED
    if verdict == HumanVerdict.CORRECT:
        return TrainingLabel.POSITIVE_HUMAN_CONFIRMED
    return TrainingLabel.UNKNOWN_INCONCLUSIVE


def feedback_to_dict(feedback: HumanFeedbackCaptcha) -> dict[str, Any]:
    return {
        "feedback_id": feedback.feedback_id,
        "analysis_id": feedback.analysis_id,
        "occurrence_id": feedback.occurrence_id,
        "thread_id": feedback.thread_id,
        "reference_key": feedback.reference_key,
        "event_type": feedback.event_type.value,
        "human_verdict": feedback.human_verdict.value,
        "confidence_human": float(feedback.confidence_human),
        "reason_code": feedback.reason_code.value,
        "target_sector": feedback.target_sector.value,
        "evidence_ref": feedback.evidence_ref,
        "reviewer_subject": feedback.reviewer_subject,
        "reviewer_sector": feedback.reviewer_sector.value,
        "created_at": feedback.created_at,
        "training_label": feedback.training_label.value,
        "model_version": feedback.model_version,
        "engine_version": feedback.engine_version,
        "notes_redacted": feedback.notes_redacted,
        "metadata": feedback.metadata,
    }


def feedback_from_dict(payload: dict[str, Any]) -> HumanFeedbackCaptcha:
    return HumanFeedbackCaptcha(
        feedback_id=str(payload["feedback_id"]),
        analysis_id=str(payload["analysis_id"]),
        occurrence_id=str(payload["occurrence_id"]),
        thread_id=str(payload["thread_id"]),
        reference_key=str(payload["reference_key"]),
        event_type=str(payload["event_type"]),
        human_verdict=str(payload["human_verdict"]),
        confidence_human=float(payload["confidence_human"]),
        reason_code=str(payload["reason_code"]),
        target_sector=str(payload["target_sector"]),
        evidence_ref=str(payload["evidence_ref"]),
        reviewer_subject=str(payload["reviewer_subject"]),
        reviewer_sector=str(payload["reviewer_sector"]),
        created_at=str(payload["created_at"]),
        training_label=str(payload["training_label"]),
        model_version=payload.get("model_version"),
        engine_version=payload.get("engine_version"),
        notes_redacted=str(payload.get("notes_redacted") or ""),
        metadata=dict(payload.get("metadata") or {}),
    )


def export_feedback_dataset(feedbacks: list[HumanFeedbackCaptcha]) -> list[dict[str, Any]]:
    return [feedback_to_dict(item) for item in feedbacks]


def _redact_text(value: str) -> str:
    return str(redact_audit_payload({"value": value}).get("value", ""))
