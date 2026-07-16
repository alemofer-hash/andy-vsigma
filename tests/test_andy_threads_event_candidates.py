from __future__ import annotations

import pytest

from andy_threads.event_candidates import (
    EventCandidate,
    EventCandidateStatus,
    EventCandidateType,
    EventEvidenceSource,
    EventValidationLevel,
    apply_feedback_to_candidate,
    candidate_from_dict,
    candidate_to_dict,
    create_centroid_candidate,
    create_conceptual_actor_critic_candidate,
    create_power_inversion_candidate,
    export_event_candidate_dataset,
)
from andy_threads.feedback import FeedbackEventType, FeedbackReasonCode, HumanFeedbackCaptcha, HumanVerdict, TrainingLabel
from andy_threads.sector_lens import SectorId


def _feedback(**overrides) -> HumanFeedbackCaptcha:
    payload = {
        "feedback_id": "fb-1",
        "analysis_id": "analysis-1",
        "occurrence_id": "occ-1",
        "thread_id": "thread-1",
        "reference_key": "VARIABLE:synthetic",
        "event_type": FeedbackEventType.SWITCHING_EVENT,
        "human_verdict": HumanVerdict.CORRECT,
        "confidence_human": 0.88,
        "reason_code": FeedbackReasonCode.OPERATIONAL_SWITCHING,
        "target_sector": SectorId.OPERATION,
        "evidence_ref": "evidence-synthetic",
        "reviewer_subject": "operator.synthetic",
        "reviewer_sector": SectorId.OPERATION,
    }
    payload.update(overrides)
    return HumanFeedbackCaptcha(**payload)


def _centroid_candidate():
    return create_centroid_candidate(
        candidate_id="cand-1",
        occurrence_id="occ-1",
        thread_id="thread-1",
        reference_key="VARIABLE:synthetic",
        score=0.76,
        centroid_metrics={"delta_norm": 0.42, "threshold": 0.30},
        notes_redacted=r"Recorte sintetico em C:\Users\Someone\secret.xlsx",
    )


def test_centroid_candidate_starts_as_statistical_candidate_only() -> None:
    candidate = _centroid_candidate()

    assert candidate.candidate_type == EventCandidateType.CENTROID_DISPLACEMENT_ANOMALY
    assert candidate.status == EventCandidateStatus.CANDIDATE
    assert candidate.validation_level == EventValidationLevel.STATISTICAL_CANDIDATE
    assert not candidate.is_operationally_confirmed
    assert EventEvidenceSource.CENTROID_THRESHOLD in candidate.evidence_sources


def test_human_switching_feedback_confirms_human_but_not_operational_scada() -> None:
    reviewed = apply_feedback_to_candidate(_centroid_candidate(), _feedback())

    assert reviewed.status == EventCandidateStatus.HUMAN_CONFIRMED
    assert reviewed.validation_level == EventValidationLevel.HUMAN_CONFIRMED
    assert EventEvidenceSource.HUMAN_FEEDBACK in reviewed.evidence_sources
    assert EventEvidenceSource.SCADA_LABEL not in reviewed.evidence_sources
    assert not reviewed.is_operationally_confirmed


def test_scada_feedback_promotes_candidate_to_operational_confirmation() -> None:
    reviewed = apply_feedback_to_candidate(
        _centroid_candidate(),
        _feedback(reason_code=FeedbackReasonCode.SCADA_CONFIRMS, reviewer_sector=SectorId.PROTECTION_AUTOMATION),
    )

    assert reviewed.status == EventCandidateStatus.SCADA_CONFIRMED
    assert reviewed.validation_level == EventValidationLevel.OPERATIONAL_SCADA_CONFIRMED
    assert EventEvidenceSource.SCADA_LABEL in reviewed.evidence_sources
    assert reviewed.is_operationally_confirmed


def test_false_positive_feedback_rejects_candidate_for_training_dataset() -> None:
    reviewed = apply_feedback_to_candidate(
        _centroid_candidate(),
        _feedback(
            human_verdict=HumanVerdict.FALSE_POSITIVE,
            reason_code=FeedbackReasonCode.SCADA_DOES_NOT_CONFIRM,
            reviewer_sector=SectorId.PROTECTION_AUTOMATION,
        ),
    )

    assert reviewed.status == EventCandidateStatus.FALSE_POSITIVE
    assert reviewed.validation_level == EventValidationLevel.REJECTED
    assert not reviewed.is_operationally_confirmed


def test_inconclusive_feedback_keeps_candidate_out_of_positive_training() -> None:
    reviewed = apply_feedback_to_candidate(
        _centroid_candidate(),
        _feedback(
            human_verdict=HumanVerdict.NOT_ENOUGH_EVIDENCE,
            reason_code=FeedbackReasonCode.NO_EVIDENCE,
            target_sector=SectorId.MEASUREMENT_DATA,
        ),
    )

    assert reviewed.status == EventCandidateStatus.INCONCLUSIVE
    assert reviewed.validation_level == EventValidationLevel.STATISTICAL_CANDIDATE
    assert not reviewed.is_operationally_confirmed


def test_conceptual_actor_critic_candidate_remains_quarantined() -> None:
    candidate = create_conceptual_actor_critic_candidate(
        candidate_id="concept-1",
        occurrence_id="occ-1",
        thread_id="thread-1",
        reference_key="VARIABLE:synthetic",
        feature_summary={"paper_state": "conceptual_without_scada_labels"},
    )

    assert candidate.status == EventCandidateStatus.QUARANTINED
    assert candidate.validation_level == EventValidationLevel.CONCEPTUAL_ONLY
    assert candidate.is_conceptual_only
    with pytest.raises(ValueError, match="conceptual_candidate_cannot_be_promoted_by_feedback"):
        apply_feedback_to_candidate(candidate, _feedback(reason_code=FeedbackReasonCode.SCADA_CONFIRMS))


def test_rejects_invalid_operational_or_decision_states() -> None:
    with pytest.raises(ValueError, match="candidate_score_out_of_range"):
        create_power_inversion_candidate(
            candidate_id="bad-score",
            occurrence_id="occ-1",
            thread_id="thread-1",
            reference_key="VARIABLE:synthetic",
            score=1.2,
            feature_summary={},
        )
    with pytest.raises(ValueError, match="event_candidate_cannot_apply_operational_decision"):
        EventCandidate(
            candidate_id="bad-decision",
            occurrence_id="occ-1",
            thread_id="thread-1",
            reference_key="VARIABLE:synthetic",
            candidate_type=EventCandidateType.SWITCHING_CANDIDATE,
            status=EventCandidateStatus.CANDIDATE,
            validation_level=EventValidationLevel.STATISTICAL_CANDIDATE,
            score=0.4,
            evidence_sources=(EventEvidenceSource.ANDY_ENGINE,),
            decision_applied=True,
        )
    with pytest.raises(ValueError, match="scada_confirmed_candidate_requires_scada_label"):
        EventCandidate(
            candidate_id="bad-scada",
            occurrence_id="occ-1",
            thread_id="thread-1",
            reference_key="VARIABLE:synthetic",
            candidate_type=EventCandidateType.SWITCHING_CANDIDATE,
            status=EventCandidateStatus.SCADA_CONFIRMED,
            validation_level=EventValidationLevel.OPERATIONAL_SCADA_CONFIRMED,
            score=0.9,
            evidence_sources=(EventEvidenceSource.ANDY_ENGINE,),
        )


def test_feedback_reference_mismatch_is_rejected() -> None:
    with pytest.raises(ValueError, match="feedback_reference_mismatch"):
        apply_feedback_to_candidate(_centroid_candidate(), _feedback(reference_key="VARIABLE:other"))


def test_candidate_dataset_roundtrips_and_redacts_sensitive_paths() -> None:
    candidate = _centroid_candidate()
    payload = candidate_to_dict(candidate)
    restored = candidate_from_dict(payload)
    dataset = export_event_candidate_dataset([restored])

    assert dataset[0]["candidate_type"] == "CENTROID_DISPLACEMENT_ANOMALY"
    assert dataset[0]["operationally_confirmed"] is False
    assert "C:\\Users\\Someone" not in dataset[0]["notes_redacted"]
    assert "[REDACTED_PATH]" in dataset[0]["notes_redacted"]


def test_feedback_label_can_feed_future_training_without_training_a_model() -> None:
    feedback = _feedback(reason_code=FeedbackReasonCode.SCADA_CONFIRMS)
    reviewed = apply_feedback_to_candidate(_centroid_candidate(), feedback)
    row = export_event_candidate_dataset([reviewed])[0]

    assert feedback.training_label == TrainingLabel.POSITIVE_SCADA_CONFIRMED
    assert row["feedback_ids"] == ["fb-1"]
    assert row["generated_by"] == "andy.experimental.proposal_only"
