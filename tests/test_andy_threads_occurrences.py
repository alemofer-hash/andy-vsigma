from __future__ import annotations

import pytest

from andy_threads.models import ThreadParticipant
from andy_threads.occurrences import (
    Occurrence,
    OccurrenceDomain,
    OccurrenceSeverity,
    OccurrenceStatus,
    create_occurrence,
    occurrence_public_summary,
)
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


def test_create_occurrence_requires_technical_reference() -> None:
    occurrence = create_occurrence(
        occurrence_id="occ-1",
        thread_id="thread-1",
        title="Inversao suspeita",
        summary="Recorte sintetico aponta inversao a revisar.",
        problem_domain=OccurrenceDomain.POWER_INVERSION,
        reference=_reference(),
        owner_sector=SectorId.ENGINEERING,
        created_by=_actor(),
    )

    assert occurrence.status == OccurrenceStatus.OPEN
    assert occurrence.reference_key.startswith("VARIABLE:")
    assert occurrence.owner_sector == SectorId.ENGINEERING


def test_occurrence_rejects_generic_chat_without_valid_reference() -> None:
    with pytest.raises(ValueError, match="occurrence_reference_invalid:technical_identifier_required"):
        Occurrence(
            occurrence_id="occ-generic",
            thread_id="thread-generic",
            title="Conversa generica",
            summary="Nao deve existir sem recorte tecnico.",
            problem_domain=OccurrenceDomain.ELECTRICAL_PARAMETER,
            reference=AndyThreadReference(ThreadEntityType.MEASUREMENT_POINT),
            owner_sector=SectorId.ENGINEERING,
            created_by=_actor(),
        )


def test_forwarded_occurrence_requires_target_sector() -> None:
    with pytest.raises(ValueError, match="forwarded_occurrence_requires_target_sector"):
        Occurrence(
            occurrence_id="occ-forward",
            thread_id="thread-forward",
            title="Encaminhar",
            summary="Encaminhamento sem setor nao e auditavel.",
            problem_domain=OccurrenceDomain.MEASUREMENT_AVAILABILITY,
            reference=_reference(),
            owner_sector=SectorId.ENGINEERING,
            created_by=_actor(),
            status=OccurrenceStatus.FORWARDED,
        )


def test_occurrence_can_move_to_in_progress_forwarded_finalized_and_archived() -> None:
    occurrence = create_occurrence(
        occurrence_id="occ-flow",
        thread_id="thread-flow",
        title="Lacuna de medicao",
        summary="Validar disponibilidade do recorte.",
        problem_domain=OccurrenceDomain.MEASUREMENT_AVAILABILITY,
        reference=_reference(),
        owner_sector=SectorId.MEASUREMENT_DATA,
        created_by=_actor(),
    )

    in_progress = occurrence.transition(OccurrenceStatus.IN_PROGRESS, actor=_actor())
    forwarded = in_progress.transition(
        OccurrenceStatus.FORWARDED,
        actor=_actor(),
        target_sector=SectorId.MEASUREMENT_DATA,
    )
    finalized = forwarded.transition(
        OccurrenceStatus.FINALIZED,
        actor=_actor(),
        closure_reason="Synthetic measurement check resolved.",
    )
    archived = finalized.transition(
        OccurrenceStatus.ARCHIVED,
        actor=_actor(),
        closure_reason="Synthetic archive after closure.",
    )

    assert in_progress.status == OccurrenceStatus.IN_PROGRESS
    assert forwarded.status == OccurrenceStatus.FORWARDED
    assert forwarded.target_sector == SectorId.MEASUREMENT_DATA
    assert finalized.status == OccurrenceStatus.FINALIZED
    assert finalized.closed_at
    assert archived.status == OccurrenceStatus.ARCHIVED


def test_high_risk_occurrence_requires_evidence_or_decision_before_closure() -> None:
    occurrence = create_occurrence(
        occurrence_id="occ-risk",
        thread_id="thread-risk",
        title="Risco operacional",
        summary="Manobra candidata precisa evidencia antes de fechar.",
        problem_domain=OccurrenceDomain.SWITCHING_EVENT,
        reference=_reference(),
        owner_sector=SectorId.OPERATION,
        created_by=_actor(),
        severity=OccurrenceSeverity.S3_OPERATIONAL_RISK,
    )

    with pytest.raises(ValueError, match="high_risk_occurrence_requires_evidence_or_decision_before_closure"):
        occurrence.transition(
            OccurrenceStatus.FINALIZED,
            actor=_actor(),
            closure_reason="Nao pode fechar sem evidencia.",
        )

    closed = occurrence.transition(
        OccurrenceStatus.FINALIZED,
        actor=_actor(),
        closure_reason="SCADA synthetic evidence reviewed.",
        evidence_refs=("evidence-synthetic-scada",),
    )
    assert closed.status == OccurrenceStatus.FINALIZED
    assert closed.evidence_refs == ("evidence-synthetic-scada",)


def test_public_summary_is_redacted_and_auditable() -> None:
    occurrence = create_occurrence(
        occurrence_id="occ-summary",
        thread_id="thread-summary",
        title="Resumo",
        summary="Resumo publico sintetico.",
        problem_domain=OccurrenceDomain.EXPORT_DASHBOARD,
        reference=_reference(),
        owner_sector=SectorId.ENGINEERING,
        created_by=_actor(),
        metadata={"raw_values": ["must_not_appear"]},
    )

    summary = occurrence_public_summary(occurrence)
    assert summary["occurrence_id"] == "occ-summary"
    assert summary["reference_key"].startswith("VARIABLE:")
    assert "raw_values" not in summary
