from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from andy_threads.event_candidates import (
    EventCandidateStatus,
    EventValidationLevel,
    apply_feedback_to_candidate,
    create_centroid_candidate,
    create_conceptual_actor_critic_candidate,
    export_event_candidate_dataset,
)
from andy_threads.feedback import FeedbackEventType, FeedbackReasonCode, HumanFeedbackCaptcha, HumanVerdict
from andy_threads.sector_lens import SectorId


def _feedback(reason_code: FeedbackReasonCode, *, feedback_id: str, verdict: HumanVerdict = HumanVerdict.CORRECT) -> HumanFeedbackCaptcha:
    return HumanFeedbackCaptcha(
        feedback_id=feedback_id,
        analysis_id="analysis-check",
        occurrence_id="occ-check",
        thread_id="thread-check",
        reference_key="VARIABLE:synthetic",
        event_type=FeedbackEventType.SWITCHING_EVENT,
        human_verdict=verdict,
        confidence_human=0.87,
        reason_code=reason_code,
        target_sector=SectorId.OPERATION,
        evidence_ref="evidence-synthetic",
        reviewer_subject="operator.synthetic",
        reviewer_sector=SectorId.OPERATION,
    )


def main() -> int:
    candidate = create_centroid_candidate(
        candidate_id="cand-check",
        occurrence_id="occ-check",
        thread_id="thread-check",
        reference_key="VARIABLE:synthetic",
        score=0.74,
        centroid_metrics={"delta_norm": 0.41, "threshold": 0.30},
    )
    if candidate.is_operationally_confirmed:
        print("ANDY Threads event candidates: failed")
        print("reason=statistical_candidate_became_operational")
        return 1

    human = apply_feedback_to_candidate(candidate, _feedback(FeedbackReasonCode.OPERATIONAL_SWITCHING, feedback_id="fb-human"))
    if human.status != EventCandidateStatus.HUMAN_CONFIRMED or human.is_operationally_confirmed:
        print("ANDY Threads event candidates: failed")
        print("reason=human_feedback_wrong_promotion")
        return 1

    scada = apply_feedback_to_candidate(candidate, _feedback(FeedbackReasonCode.SCADA_CONFIRMS, feedback_id="fb-scada"))
    if not scada.is_operationally_confirmed:
        print("ANDY Threads event candidates: failed")
        print("reason=scada_feedback_did_not_promote")
        return 1

    false_positive = apply_feedback_to_candidate(
        candidate,
        _feedback(FeedbackReasonCode.SCADA_DOES_NOT_CONFIRM, feedback_id="fb-false", verdict=HumanVerdict.FALSE_POSITIVE),
    )
    if false_positive.validation_level != EventValidationLevel.REJECTED:
        print("ANDY Threads event candidates: failed")
        print("reason=false_positive_not_rejected")
        return 1

    conceptual = create_conceptual_actor_critic_candidate(
        candidate_id="concept-check",
        occurrence_id="occ-check",
        thread_id="thread-check",
        reference_key="VARIABLE:synthetic",
    )
    if conceptual.is_operationally_confirmed or not conceptual.is_conceptual_only:
        print("ANDY Threads event candidates: failed")
        print("reason=conceptual_candidate_not_quarantined")
        return 1

    dataset = export_event_candidate_dataset([candidate, human, scada, false_positive, conceptual])
    print("ANDY Threads event candidates: passed")
    print("proposal_only=true")
    print("operational_without_scada=false")
    print("rows=" + str(len(dataset)))
    print("statuses=" + ",".join(row["status"] for row in dataset))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
