from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from andy_threads.feedback import (
    FeedbackEventType,
    FeedbackReasonCode,
    HumanFeedbackCaptcha,
    HumanVerdict,
    TrainingLabel,
    export_feedback_dataset,
)
from andy_threads.sector_lens import SectorId


def main() -> int:
    feedback = HumanFeedbackCaptcha(
        feedback_id="fb-check",
        analysis_id="analysis-check",
        occurrence_id="occ-check",
        thread_id="thread-check",
        reference_key="VARIABLE:synthetic",
        event_type=FeedbackEventType.SWITCHING_EVENT,
        human_verdict=HumanVerdict.CORRECT,
        confidence_human=0.85,
        reason_code=FeedbackReasonCode.OPERATIONAL_SWITCHING,
        target_sector=SectorId.OPERATION,
        evidence_ref="evidence-synthetic",
        reviewer_subject="operator.synthetic",
        reviewer_sector=SectorId.OPERATION,
    )
    false_positive = HumanFeedbackCaptcha(
        feedback_id="fb-check-fp",
        analysis_id="analysis-check-fp",
        occurrence_id="occ-check-fp",
        thread_id="thread-check-fp",
        reference_key="VARIABLE:synthetic",
        event_type=FeedbackEventType.POWER_INVERSION,
        human_verdict=HumanVerdict.FALSE_POSITIVE,
        confidence_human=0.9,
        reason_code=FeedbackReasonCode.MEASUREMENT_BAD_QUALITY,
        target_sector=SectorId.MEASUREMENT_DATA,
        evidence_ref="evidence-synthetic-fp",
        reviewer_subject="engineer.synthetic",
        reviewer_sector=SectorId.ENGINEERING,
    )
    dataset = export_feedback_dataset([feedback, false_positive])
    if feedback.training_label != TrainingLabel.POSITIVE_HUMAN_CONFIRMED:
        print("ANDY Threads feedback: failed")
        print("reason=switching_without_scada_should_not_be_scada_confirmed")
        return 1
    if false_positive.is_positive_training_label:
        print("ANDY Threads feedback: failed")
        print("reason=false_positive_became_positive")
        return 1
    print("ANDY Threads feedback: passed")
    print(f"labels={','.join(item['training_label'] for item in dataset)}")
    print("scada_operational_confirmation=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
