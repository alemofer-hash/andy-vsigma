from __future__ import annotations

import pytest

from andy_threads import (
    AndyThread,
    AndyThreadReference,
    DecisionRecord,
    DecisionType,
    ThreadEntityType,
    ThreadKind,
    ThreadMessage,
    ThreadParticipant,
    ThreadStatus,
)


def _participant() -> ThreadParticipant:
    return ThreadParticipant("engineer.synthetic", "Engineer Synthetic", "ENGINEERING")


def _reference() -> AndyThreadReference:
    return AndyThreadReference(ThreadEntityType.MEASUREMENT_POINT, se="SE1", bay_or_feeder="AL1", terminal="T1")


def test_thread_requires_technical_reference() -> None:
    with pytest.raises(ValueError, match="thread_reference_invalid"):
        AndyThread(
            "thread-1",
            "Invalid",
            ThreadKind.GENERAL_REVIEW,
            AndyThreadReference(ThreadEntityType.MEASUREMENT_POINT),
            _participant(),
        )


def test_message_requires_thread_id() -> None:
    with pytest.raises(ValueError, match="message_thread_id_required"):
        ThreadMessage("msg-1", "", _participant(), "body")


def test_decision_requires_evidence_refs() -> None:
    with pytest.raises(ValueError, match="decision_evidence_refs_required"):
        DecisionRecord("decision-1", "thread-1", DecisionType.MEASUREMENT_VALIDATED, "ok", _participant(), ())


def test_resolved_thread_requires_decision_or_reason() -> None:
    with pytest.raises(ValueError, match="resolved_thread_requires_decision_or_reason"):
        AndyThread("thread-1", "Resolved", ThreadKind.DATA_QUALITY, _reference(), _participant(), status=ThreadStatus.RESOLVED)


def test_valid_thread_accepts_reference() -> None:
    thread = AndyThread("thread-1", "Valid", ThreadKind.DATA_QUALITY, _reference(), _participant())
    assert thread.status == ThreadStatus.OPEN
