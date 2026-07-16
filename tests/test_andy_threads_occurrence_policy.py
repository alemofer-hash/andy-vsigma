from __future__ import annotations

from andy_threads.models import ThreadParticipant
from andy_threads.occurrences import OccurrenceDomain, OccurrenceStatus, create_occurrence
from andy_threads.policy import (
    MockThreadUserContext,
    OccurrenceAccessRequest,
    OccurrenceAction,
    evaluate_occurrence_access,
)
from andy_threads.references import AndyThreadReference, ThreadEntityType
from andy_threads.sector_lens import SectorId


def _occurrence():
    reference = AndyThreadReference(ThreadEntityType.VARIABLE, se="SE1", bay_or_feeder="AL1", variavel="MW")
    actor = ThreadParticipant("engineer.synthetic", "Engineer Synthetic", SectorId.ENGINEERING.value)
    return create_occurrence(
        occurrence_id="occ-policy",
        thread_id="thread-policy",
        title="Policy",
        summary="Synthetic policy occurrence.",
        problem_domain=OccurrenceDomain.POWER_INVERSION,
        reference=reference,
        owner_sector=SectorId.ENGINEERING,
        created_by=actor,
        target_sector=SectorId.OPERATION,
    ).transition(OccurrenceStatus.FORWARDED, actor=actor, target_sector=SectorId.OPERATION)


def test_occurrence_policy_denies_without_identity() -> None:
    decision = evaluate_occurrence_access(
        OccurrenceAccessRequest(OccurrenceAction.READ_OCCURRENCE, None, occurrence=_occurrence())
    )
    assert not decision.allowed
    assert decision.reason == "identity_required"


def test_occurrence_policy_allows_owner_create_and_target_read() -> None:
    occurrence = _occurrence()
    owner = MockThreadUserContext("engineer.synthetic", "ENGINEERING", substations=("SE1",), feeders=("AL1",))
    target = MockThreadUserContext("operator.synthetic", "OPERATION", substations=("SE1",), feeders=("AL1",))

    create_decision = evaluate_occurrence_access(
        OccurrenceAccessRequest(OccurrenceAction.CREATE_OCCURRENCE, owner, occurrence=occurrence)
    )
    read_decision = evaluate_occurrence_access(
        OccurrenceAccessRequest(OccurrenceAction.READ_OCCURRENCE, target, occurrence=occurrence)
    )

    assert create_decision.allowed
    assert read_decision.allowed


def test_occurrence_policy_blocks_out_of_scope_and_requires_export_permission() -> None:
    occurrence = _occurrence()
    out_of_scope = MockThreadUserContext("engineer.synthetic", "ENGINEERING", substations=("OTHER",), feeders=("AL1",))
    no_export = MockThreadUserContext("engineer.synthetic", "ENGINEERING", substations=("SE1",), feeders=("AL1",))
    export_user = MockThreadUserContext(
        "auditor.synthetic",
        "ENGINEERING",
        substations=("SE1",),
        feeders=("AL1",),
        can_export_threads=True,
    )

    denied_scope = evaluate_occurrence_access(
        OccurrenceAccessRequest(OccurrenceAction.READ_OCCURRENCE, out_of_scope, occurrence=occurrence)
    )
    denied_export = evaluate_occurrence_access(
        OccurrenceAccessRequest(OccurrenceAction.EXPORT_OCCURRENCE, no_export, occurrence=occurrence)
    )
    allowed_export = evaluate_occurrence_access(
        OccurrenceAccessRequest(OccurrenceAction.EXPORT_OCCURRENCE, export_user, occurrence=occurrence)
    )

    assert not denied_scope.allowed
    assert denied_scope.reason == "reference_outside_user_scope"
    assert not denied_export.allowed
    assert denied_export.reason == "export_permission_required"
    assert allowed_export.allowed
