from __future__ import annotations

from andy_threads.models import ThreadParticipant
from andy_threads.notification_intent import (
    NotificationIntentStatus,
    build_notification_intent,
    notification_intent_to_dict,
)
from andy_threads.occurrences import OccurrenceDomain, OccurrenceStatus, create_occurrence
from andy_threads.references import AndyThreadReference, ThreadEntityType
from andy_threads.sector_lens import SectorId


def _reference() -> AndyThreadReference:
    return AndyThreadReference(
        ThreadEntityType.EQUIPMENT,
        se="SE1",
        bay_or_feeder="AL1",
        equipamento="EQ1",
    )


def _actor() -> ThreadParticipant:
    return ThreadParticipant("engineer.synthetic", "Engineer Synthetic", SectorId.ENGINEERING.value)


def test_notification_intent_is_draft_or_ready_and_never_sends() -> None:
    occurrence = create_occurrence(
        occurrence_id="occ-intent",
        thread_id="thread-intent",
        title="Encaminhar para operacao",
        summary="Validar manobra candidata no recorte sintetico.",
        problem_domain=OccurrenceDomain.SWITCHING_EVENT,
        reference=_reference(),
        owner_sector=SectorId.ENGINEERING,
        created_by=_actor(),
        target_sector=SectorId.OPERATION,
    ).transition(OccurrenceStatus.FORWARDED, actor=_actor(), target_sector=SectorId.OPERATION)

    intent = build_notification_intent(
        intent_id="intent-1",
        occurrence=occurrence,
        created_by=_actor().subject,
    )
    ready = intent.mark_ready_for_human_send()
    payload = notification_intent_to_dict(ready)

    assert intent.status == NotificationIntentStatus.DRAFT
    assert ready.status == NotificationIntentStatus.READY_FOR_HUMAN_SEND
    assert payload["real_provider_enabled"] is False
    assert "nao envia e-mail/Teams automaticamente" in ready.body_redacted
    assert ready.target_sector == SectorId.OPERATION


def test_notification_intent_redacts_paths_and_sensitive_metadata() -> None:
    occurrence = create_occurrence(
        occurrence_id="occ-redact",
        thread_id="thread-redact",
        title="Redacao",
        summary=r"Falha em C:\Users\Someone\secret\file.xlsx e token=abc.",
        problem_domain=OccurrenceDomain.TOOL_RUNTIME,
        reference=_reference(),
        owner_sector=SectorId.IT_BI_DATA,
        created_by=_actor(),
    )

    intent = build_notification_intent(
        intent_id="intent-redact",
        occurrence=occurrence,
        created_by=_actor().subject,
    )
    payload = notification_intent_to_dict(intent)

    assert "C:\\Users\\Someone" not in payload["body_redacted"]
    assert "[REDACTED_PATH]" in payload["body_redacted"]
    assert payload["real_provider_enabled"] is False
