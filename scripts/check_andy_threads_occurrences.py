from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from andy_threads.models import ThreadParticipant
from andy_threads.notification_intent import build_notification_intent
from andy_threads.occurrence_store import OccurrenceStore
from andy_threads.occurrences import OccurrenceDomain, OccurrenceSeverity, OccurrenceStatus, create_occurrence
from andy_threads.policy import MockThreadUserContext, OccurrenceAccessRequest, OccurrenceAction, evaluate_occurrence_access
from andy_threads.references import AndyThreadReference, ThreadEntityType
from andy_threads.sector_lens import SectorId


def main() -> int:
    root = ROOT / ".validation_tmp" / "andy_threads_session" / "check_occurrences"
    store = OccurrenceStore(root / "occurrences.sqlite")
    actor = ThreadParticipant("engineer.synthetic", "Engineer Synthetic", SectorId.ENGINEERING.value)
    reference = AndyThreadReference(
        ThreadEntityType.VARIABLE,
        se="SE_SYN",
        bay_or_feeder="AL_SYN",
        equipamento="EQ_SYN",
        terminal="T_SYN",
        variavel="MW",
        period_start="2026",
        period_end="2026",
    )
    occurrence = create_occurrence(
        occurrence_id="occ-check",
        thread_id="thread-check",
        title="Synthetic occurrence check",
        summary="Synthetic occurrence for readiness gate.",
        problem_domain=OccurrenceDomain.POWER_INVERSION,
        reference=reference,
        owner_sector=SectorId.ENGINEERING,
        created_by=actor,
        severity=OccurrenceSeverity.S2_ENGINEERING_BLOCKER,
    )
    store.create_occurrence(occurrence)
    forwarded = store.change_status(
        occurrence,
        OccurrenceStatus.FORWARDED,
        actor=actor,
        target_sector=SectorId.OPERATION,
    )
    intent = build_notification_intent(
        intent_id="intent-check",
        occurrence=forwarded,
        created_by=actor.subject,
    ).mark_ready_for_human_send()
    store.create_notification_intent(intent, actor=actor.subject)
    exported = store.export_occurrence(occurrence.occurrence_id, "json")
    user = MockThreadUserContext("engineer.synthetic", "ENGINEERING", substations=("SE_SYN",), feeders=("AL_SYN",))
    decision = evaluate_occurrence_access(
        OccurrenceAccessRequest(OccurrenceAction.READ_OCCURRENCE, user, occurrence=forwarded)
    )
    if not decision.allowed:
        print("ANDY Threads occurrences: failed")
        print(f"reason={decision.reason}")
        return 1
    if not exported["notification_intents"] or exported["notification_intents"][0]["real_provider_enabled"] is not False:
        print("ANDY Threads occurrences: failed")
        print("reason=notification_intent_not_redacted_or_provider_enabled")
        return 1
    print("ANDY Threads occurrences: passed")
    print(f"occurrence_id={occurrence.occurrence_id}")
    print(f"status={forwarded.status.value}")
    print(f"intent_status={intent.status.value}")
    print(f"store={store.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
