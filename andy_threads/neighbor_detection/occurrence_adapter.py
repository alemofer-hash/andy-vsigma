from __future__ import annotations

import uuid

from andy_threads.event_candidates import EventCandidate, create_centroid_candidate
from andy_threads.models import AndyThread, ThreadKind, ThreadMessage, ThreadParticipant, ThreadPriority, ThreadStatus
from andy_threads.notification_intent import build_notification_intent, notification_intent_to_dict
from andy_threads.occurrences import (
    FeedbackStatus,
    Occurrence,
    OccurrenceDomain,
    OccurrenceSeverity,
    OccurrenceStatus,
    create_occurrence,
    occurrence_public_summary,
)
from andy_threads.references import AndyThreadReference, ThreadEntityType, reference_key
from andy_threads.sector_lens import SectorId

from .models import NeighborManeuverCandidate, NeighborhoodEventEpisode, to_plain_dict

SYSTEM_PARTICIPANT = ThreadParticipant(subject="andy.neighbor_detection", display_name="ANDY Neighbor Detection", sector_id=SectorId.OPERATION.value)


def episode_to_thread_bundle(
    episode: NeighborhoodEventEpisode,
    candidates: list[NeighborManeuverCandidate],
) -> dict[str, object]:
    primary = max(candidates, key=lambda item: item.transfer_score)
    thread_id = "thread-" + episode.episode_id
    occurrence_id = "occ-" + episode.episode_id
    ref = AndyThreadReference(
        entity_type=ThreadEntityType.POWER_FLOW_EVENT,
        source_fingerprint=primary.source_hash[:16],
        se=episode.SE,
        bay_or_feeder="/".join(primary.feeder_pair),
        equipamento=";".join(primary.equipment_by_feeder.values()),
        terminal=primary.terminal,
        variavel="IB",
        period_start=episode.event_start,
        period_end=episode.event_end,
        source_cadence=f"{primary.cadence_seconds}s" if primary.cadence_seconds else None,
        anomaly_id=episode.episode_id,
    )
    title = f"Possivel transferencia de carga - {episode.SE} / {primary.feeder_pair[0]} <-> {primary.feeder_pair[1]}"
    summary = (
        "O ANDY detectou alteracoes sincronizadas nas correntes IB de alimentadores distintos. "
        "O padrao e compativel com transferencia/manobra, mas permanece candidato ate validacao humana."
    )
    occurrence = create_occurrence(
        occurrence_id=occurrence_id,
        thread_id=thread_id,
        title=title,
        summary=summary,
        problem_domain=OccurrenceDomain.SWITCHING_EVENT,
        reference=ref,
        owner_sector=SectorId.OPERATION,
        created_by=SYSTEM_PARTICIPANT,
        severity=OccurrenceSeverity.S3_OPERATIONAL_RISK,
        target_sector=SectorId.PROTECTION_AUTOMATION,
        tags=("neighbor_detection", "ib_pair", "candidate_only"),
        metadata={
            "consulted_sectors": [SectorId.ENGINEERING.value, SectorId.PROTECTION_AUTOMATION.value, SectorId.MEASUREMENT_DATA.value],
            "training_use": False,
            "episode": to_plain_dict(episode),
        },
    )
    occurrence = Occurrence(
        **{
            **occurrence.__dict__,
            "status": OccurrenceStatus.WAITING_HUMAN_FEEDBACK,
            "feedback_status": FeedbackStatus.REQUESTED,
            "evidence_refs": tuple(item.candidate_id for item in candidates),
        }
    )
    thread = AndyThread(
        thread_id=thread_id,
        title=title,
        kind=ThreadKind.SWITCHING_EVENT,
        reference=ref,
        created_by=SYSTEM_PARTICIPANT,
        status=ThreadStatus.WAITING_OPERATION,
        priority=ThreadPriority.HIGH,
        owner_sector=SectorId.OPERATION.value,
        tags=("neighbor_detection", "candidate_only", "ib"),
        messages=[
            ThreadMessage(
                message_id=f"msg-{uuid.uuid4()}",
                thread_id=thread_id,
                author=SYSTEM_PARTICIPANT,
                body=summary,
                message_kind="SYSTEM_EVENT",
                metadata={"candidate_only": True, "human_validation_required": True},
            )
        ],
    )
    event_candidates = [
        _event_candidate_from_neighbor(item, occurrence_id=occurrence.occurrence_id, thread_id=thread.thread_id, ref_key=reference_key(ref))
        for item in candidates
    ]
    notification_intent = build_notification_intent(
        intent_id="intent-" + episode.episode_id,
        occurrence=occurrence,
        target_channel="MANUAL_EMAIL",
        created_by=SYSTEM_PARTICIPANT.subject,
        status="DRAFT",
    )
    return {
        "thread": _thread_to_dict(thread),
        "occurrence": occurrence_public_summary(occurrence) | {"summary": occurrence.summary, "metadata": occurrence.metadata},
        "event_candidates": [to_plain_dict(item) for item in event_candidates],
        "notification_intent": notification_intent_to_dict(notification_intent),
        "dispatched": False,
    }


def _event_candidate_from_neighbor(
    candidate: NeighborManeuverCandidate,
    *,
    occurrence_id: str,
    thread_id: str,
    ref_key: str,
) -> EventCandidate:
    return create_centroid_candidate(
        candidate_id="event-" + candidate.candidate_id,
        occurrence_id=occurrence_id,
        thread_id=thread_id,
        reference_key=ref_key,
        score=candidate.transfer_score,
        centroid_metrics={
            "centroid_delta_vector": candidate.centroid_delta_vector,
            "centroid_delta_magnitude": candidate.centroid_delta_magnitude,
            "threshold": candidate.threshold,
            "ib_only_neighbor_pair": True,
        },
        model_version=candidate.detector_version,
        notes_redacted="Candidate only. No SCADA or human validation applied.",
        metadata={
            "classification": candidate.classification.value,
            "feeder_pair": list(candidate.feeder_pair),
            "delta_I_by_feeder": candidate.delta_I_by_feeder,
            "score_components": candidate.score_components,
            "training_use": False,
        },
    )


def _thread_to_dict(thread: AndyThread) -> dict[str, object]:
    return {
        "thread_id": thread.thread_id,
        "title": thread.title,
        "kind": thread.kind.value,
        "status": thread.status.value,
        "priority": thread.priority.value,
        "owner_sector": thread.owner_sector,
        "tags": list(thread.tags),
        "messages": [
            {
                "message_id": message.message_id,
                "author": message.author.display_name,
                "body": message.body,
                "message_kind": message.message_kind.value,
                "created_at": message.created_at,
                "metadata": message.metadata,
            }
            for message in thread.messages
        ],
    }
