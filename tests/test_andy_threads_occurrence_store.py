from __future__ import annotations

from andy_threads.models import ThreadParticipant
from andy_threads.notification_intent import build_notification_intent
from andy_threads.occurrence_store import OccurrenceStore
from andy_threads.occurrences import OccurrenceDomain, OccurrenceSeverity, OccurrenceStatus, create_occurrence
from andy_threads.references import AndyThreadReference, ThreadEntityType
from andy_threads.sector_lens import SectorId


def _reference() -> AndyThreadReference:
    return AndyThreadReference(
        ThreadEntityType.VARIABLE,
        se="SE1",
        bay_or_feeder="AL1",
        equipamento="EQ1",
        terminal="T1",
        variavel="MW",
        period_start="2026",
        period_end="2026",
    )


def _actor() -> ThreadParticipant:
    return ThreadParticipant("engineer.synthetic", "Engineer Synthetic", SectorId.ENGINEERING.value)


def _occurrence():
    return create_occurrence(
        occurrence_id="occ-store",
        thread_id="thread-store",
        title="Synthetic occurrence",
        summary="Synthetic occurrence for local store.",
        problem_domain=OccurrenceDomain.POWER_INVERSION,
        reference=_reference(),
        owner_sector=SectorId.ENGINEERING,
        created_by=_actor(),
        severity=OccurrenceSeverity.S2_ENGINEERING_BLOCKER,
    )


def test_occurrence_store_creates_lists_changes_status_and_exports(tmp_path) -> None:
    store = OccurrenceStore(tmp_path / "occurrences.sqlite")
    occurrence = _occurrence()

    store.create_occurrence(occurrence)
    stored = store.get_occurrence(occurrence.occurrence_id)
    assert stored["occurrence_id"] == occurrence.occurrence_id
    assert stored["reference_key"].startswith("VARIABLE:")
    assert store.list_occurrences(reference=occurrence.reference)

    forwarded = store.change_status(
        occurrence,
        OccurrenceStatus.FORWARDED,
        actor=_actor(),
        target_sector=SectorId.MEASUREMENT_DATA,
    )
    assert forwarded.status == OccurrenceStatus.FORWARDED
    assert store.list_occurrences(status=OccurrenceStatus.FORWARDED)
    assert store.list_occurrences(target_sector=SectorId.MEASUREMENT_DATA)

    finalized = store.change_status(
        forwarded,
        OccurrenceStatus.FINALIZED,
        actor=_actor(),
        closure_reason="Synthetic resolution.",
    )
    exported = store.export_occurrence(finalized.occurrence_id, "json")
    markdown = store.export_occurrence(finalized.occurrence_id, "md")
    assert isinstance(exported, dict)
    assert exported["occurrence"]["status"] == OccurrenceStatus.FINALIZED.value
    assert "OCCURRENCE_STATUS_CHANGED" in str(exported["audit_summary"])
    assert "no real provider send" in markdown


def test_occurrence_store_audits_notification_intent_without_sending(tmp_path) -> None:
    store = OccurrenceStore(tmp_path / "occurrences.sqlite")
    occurrence = _occurrence().transition(
        OccurrenceStatus.FORWARDED,
        actor=_actor(),
        target_sector=SectorId.OPERATION,
    )
    store.create_occurrence(occurrence)
    intent = build_notification_intent(
        intent_id="intent-store",
        occurrence=occurrence,
        created_by=_actor().subject,
    ).mark_ready_for_human_send()

    store.create_notification_intent(intent, actor=_actor().subject)
    stored = store.get_notification_intent(intent.intent_id)
    exported = store.export_occurrence(occurrence.occurrence_id, "json")

    assert stored["status"] == "READY_FOR_HUMAN_SEND"
    assert stored["real_provider_enabled"] is False
    assert store.list_notification_intents(occurrence.occurrence_id)
    assert "NOTIFICATION_INTENT_CREATED" in str(exported["audit_summary"])
    assert "real_provider_enabled" in str(exported["notification_intents"])
