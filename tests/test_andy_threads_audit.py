from __future__ import annotations

from andy_threads.audit import append_thread_audit_event, audit_public_summary, redact_audit_payload


def test_audit_event_is_registered() -> None:
    events = []
    append_thread_audit_event(events, thread_id="thread-audit", event_type="THREAD_CREATED", actor="user")
    assert len(events) == 1
    assert audit_public_summary(events)["event_count"] == 1


def test_audit_redacts_sensitive_payload() -> None:
    payload = redact_audit_payload(
        {
            "token": "abc",
            "message": r"see C:\Users\person\secret\file.txt",
            "source": r"\\server\share\folder",
        }
    )
    assert payload["token"] == "[REDACTED]"
    assert "[REDACTED_PATH]" in payload["message"]
    assert "[REDACTED_PATH]" in payload["source"]
