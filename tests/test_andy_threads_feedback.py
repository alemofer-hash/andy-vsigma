from __future__ import annotations

import pytest

from andy_threads.feedback import (
    FeedbackEventType,
    FeedbackReasonCode,
    HumanFeedbackCaptcha,
    HumanVerdict,
    TrainingLabel,
    derive_training_label,
    export_feedback_dataset,
    feedback_from_dict,
    feedback_to_dict,
)
from andy_threads.sector_lens import SectorId


def _feedback(**overrides) -> HumanFeedbackCaptcha:
    payload = {
        "feedback_id": "fb-1",
        "analysis_id": "analysis-1",
        "occurrence_id": "occ-1",
        "thread_id": "thread-1",
        "reference_key": "VARIABLE:synthetic",
        "event_type": FeedbackEventType.POWER_INVERSION,
        "human_verdict": HumanVerdict.CORRECT,
        "confidence_human": 0.9,
        "reason_code": FeedbackReasonCode.OTHER,
        "target_sector": SectorId.ENGINEERING,
        "evidence_ref": "evidence-synthetic",
        "reviewer_subject": "engineer.synthetic",
        "reviewer_sector": SectorId.ENGINEERING,
        "notes_redacted": "Synthetic note.",
    }
    payload.update(overrides)
    return HumanFeedbackCaptcha(**payload)


def test_feedback_derives_positive_human_label_for_confirmed_power_inversion() -> None:
    feedback = _feedback()

    assert feedback.training_label == TrainingLabel.POSITIVE_HUMAN_CONFIRMED
    assert feedback.is_positive_training_label
    assert not feedback.is_operationally_confirmed


def test_feedback_derives_scada_label_only_when_scada_confirms() -> None:
    feedback = _feedback(reason_code=FeedbackReasonCode.SCADA_CONFIRMS)

    assert feedback.training_label == TrainingLabel.POSITIVE_SCADA_CONFIRMED
    assert feedback.is_operationally_confirmed


def test_false_positive_and_inconclusive_never_become_positive() -> None:
    false_positive = _feedback(
        human_verdict=HumanVerdict.FALSE_POSITIVE,
        reason_code=FeedbackReasonCode.MEASUREMENT_BAD_QUALITY,
    )
    inconclusive = _feedback(
        human_verdict=HumanVerdict.INCONCLUSIVE,
        reason_code=FeedbackReasonCode.NO_EVIDENCE,
    )

    assert false_positive.training_label == TrainingLabel.NEGATIVE_FALSE_POSITIVE
    assert not false_positive.is_positive_training_label
    assert inconclusive.training_label == TrainingLabel.UNKNOWN_INCONCLUSIVE
    assert not inconclusive.is_positive_training_label


def test_rejects_positive_override_for_false_positive() -> None:
    with pytest.raises(ValueError, match="non_positive_verdict_cannot_have_positive_training_label"):
        _feedback(
            human_verdict=HumanVerdict.FALSE_POSITIVE,
            reason_code=FeedbackReasonCode.MEASUREMENT_BAD_QUALITY,
            training_label=TrainingLabel.POSITIVE_HUMAN_CONFIRMED,
        )


def test_switching_event_without_scada_is_not_operationally_confirmed() -> None:
    feedback = _feedback(
        event_type=FeedbackEventType.SWITCHING_EVENT,
        human_verdict=HumanVerdict.CORRECT,
        reason_code=FeedbackReasonCode.OPERATIONAL_SWITCHING,
    )

    assert feedback.training_label == TrainingLabel.POSITIVE_HUMAN_CONFIRMED
    assert not feedback.is_operationally_confirmed


def test_switching_event_rejects_scada_confirmed_label_without_scada_reason() -> None:
    with pytest.raises(ValueError, match="switching_event_scada_confirmation_requires_scada_reason"):
        _feedback(
            event_type=FeedbackEventType.SWITCHING_EVENT,
            human_verdict=HumanVerdict.CORRECT,
            reason_code=FeedbackReasonCode.OPERATIONAL_SWITCHING,
            training_label=TrainingLabel.POSITIVE_SCADA_CONFIRMED,
        )


def test_rejects_missing_reference_and_confidence_out_of_range() -> None:
    with pytest.raises(ValueError, match="reference_key_required"):
        _feedback(reference_key="")
    with pytest.raises(ValueError, match="confidence_human_out_of_range"):
        _feedback(confidence_human=1.1)


def test_export_feedback_dataset_roundtrips_and_redacts_notes() -> None:
    feedback = _feedback(notes_redacted=r"Evidence from C:\Users\Someone\secret\file.xlsx")
    payload = feedback_to_dict(feedback)
    restored = feedback_from_dict(payload)
    dataset = export_feedback_dataset([restored])

    assert dataset[0]["training_label"] == "positive_human_confirmed"
    assert "C:\\Users\\Someone" not in dataset[0]["notes_redacted"]
    assert "[REDACTED_PATH]" in dataset[0]["notes_redacted"]


def test_derive_training_label_rules_are_stable() -> None:
    assert (
        derive_training_label(FeedbackEventType.POWER_INVERSION, HumanVerdict.NOT_ENOUGH_EVIDENCE, FeedbackReasonCode.NO_EVIDENCE)
        == TrainingLabel.UNKNOWN_NO_EVIDENCE
    )
    assert (
        derive_training_label(FeedbackEventType.MEASUREMENT_GAP, HumanVerdict.NEEDS_OTHER_SECTOR, FeedbackReasonCode.OTHER)
        == TrainingLabel.ROUTED_NEEDS_SECTOR
    )
