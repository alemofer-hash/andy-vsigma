from __future__ import annotations

from andy_threads import AndyThread, AndyThreadReference, ThreadEntityType, ThreadKind, ThreadParticipant
from andy_threads.policy import MockThreadUserContext, ThreadAccessRequest, ThreadAction, evaluate_thread_access


def _thread() -> AndyThread:
    return AndyThread(
        "thread-policy",
        "Policy",
        ThreadKind.POWER_INVERSION,
        AndyThreadReference(ThreadEntityType.POWER_FLOW_EVENT, se="SE1", bay_or_feeder="AL1"),
        ThreadParticipant("engineer.synthetic", "Engineer Synthetic", "ENGINEERING"),
        owner_sector="ENGINEERING",
    )


def test_deny_by_default_without_identity() -> None:
    decision = evaluate_thread_access(ThreadAccessRequest(ThreadAction.READ_THREAD, None, thread=_thread()))
    assert not decision.allowed


def test_user_without_scope_cannot_read() -> None:
    user = MockThreadUserContext("engineer.synthetic", "ENGINEERING", substations=("OTHER",), feeders=("AL1",))
    decision = evaluate_thread_access(ThreadAccessRequest(ThreadAction.READ_THREAD, user, thread=_thread()))
    assert not decision.allowed


def test_owner_with_scope_can_create() -> None:
    user = MockThreadUserContext("engineer.synthetic", "ENGINEERING", substations=("SE1",), feeders=("AL1",))
    decision = evaluate_thread_access(ThreadAccessRequest(ThreadAction.CREATE_THREAD, user, thread=_thread()))
    assert decision.allowed


def test_consulted_sector_can_comment() -> None:
    user = MockThreadUserContext("operator.synthetic", "OPERATION", substations=("SE1",), feeders=("AL1",))
    decision = evaluate_thread_access(ThreadAccessRequest(ThreadAction.COMMENT, user, thread=_thread()))
    assert decision.allowed


def test_sector_without_authority_cannot_resolve() -> None:
    user = MockThreadUserContext("operator.synthetic", "OPERATION", substations=("SE1",), feeders=("AL1",))
    decision = evaluate_thread_access(ThreadAccessRequest(ThreadAction.CREATE_DECISION, user, thread=_thread()))
    assert not decision.allowed


def test_export_requires_permission() -> None:
    user = MockThreadUserContext("engineer.synthetic", "ENGINEERING", substations=("SE1",), feeders=("AL1",))
    denied = evaluate_thread_access(ThreadAccessRequest(ThreadAction.EXPORT_THREAD, user, thread=_thread()))
    assert not denied.allowed
    allowed_user = MockThreadUserContext(
        "auditor.synthetic",
        "ENGINEERING",
        substations=("SE1",),
        feeders=("AL1",),
        can_export_threads=True,
    )
    allowed = evaluate_thread_access(ThreadAccessRequest(ThreadAction.EXPORT_THREAD, allowed_user, thread=_thread()))
    assert allowed.allowed
