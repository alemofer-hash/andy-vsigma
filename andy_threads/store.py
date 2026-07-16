from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from .audit import append_thread_audit_event
from .models import AndyThread, DecisionRecord, ThreadAuditEvent, ThreadMessage, ThreadParticipant, ThreadStatus
from .references import AndyThreadReference, reference_key
from .serialization import thread_to_dict, thread_to_markdown


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS threads (
    thread_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    reference_key TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
"""


def initialize_store(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(target) as conn:
        conn.executescript(SCHEMA_SQL)
    return target


class ThreadStore:
    def __init__(self, path: str | Path) -> None:
        self.path = initialize_store(path)

    def create_thread(self, thread: AndyThread) -> AndyThread:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO threads(thread_id, payload_json, reference_key, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    thread.thread_id,
                    json.dumps(thread_to_dict(thread), ensure_ascii=True, sort_keys=True),
                    reference_key(thread.reference),
                    thread.status.value,
                    thread.created_at,
                    thread.updated_at,
                ),
            )
            event = ThreadAuditEvent(
                event_id=f"audit-{thread.thread_id}-created",
                thread_id=thread.thread_id,
                event_type="THREAD_CREATED",
                actor=thread.created_by.subject,
                payload={"reference_key": reference_key(thread.reference)},
            )
            _insert_audit(conn, event)
        return thread

    def get_thread(self, thread_id: str) -> dict[str, Any]:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT payload_json FROM threads WHERE thread_id = ?", (thread_id,)).fetchone()
        if not row:
            raise KeyError(thread_id)
        return json.loads(row[0])

    def list_threads_by_reference(self, reference: AndyThreadReference) -> list[dict[str, Any]]:
        key = reference_key(reference)
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute("SELECT payload_json FROM threads WHERE reference_key = ? ORDER BY created_at", (key,)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def add_message(self, message: ThreadMessage) -> ThreadMessage:
        payload = _jsonable_message(message)
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO messages(message_id, thread_id, payload_json, created_at) VALUES (?, ?, ?, ?)",
                (message.message_id, message.thread_id, json.dumps(payload, ensure_ascii=True, sort_keys=True), message.created_at),
            )
            _insert_audit(
                conn,
                ThreadAuditEvent(
                    event_id=f"audit-{message.message_id}",
                    thread_id=message.thread_id,
                    event_type="MESSAGE_ADDED",
                    actor=message.author.subject,
                    payload={"message_kind": message.message_kind.value},
                ),
            )
        return message

    def change_status(self, thread_id: str, status: ThreadStatus | str, user_context: ThreadParticipant | Any) -> None:
        active_status = ThreadStatus(status)
        actor = getattr(user_context, "subject", str(user_context))
        with sqlite3.connect(self.path) as conn:
            conn.execute("UPDATE threads SET status = ? WHERE thread_id = ?", (active_status.value, thread_id))
            _insert_audit(
                conn,
                ThreadAuditEvent(
                    event_id=f"audit-{thread_id}-{active_status.value}",
                    thread_id=thread_id,
                    event_type="STATUS_CHANGED",
                    actor=actor,
                    payload={"status": active_status.value},
                ),
            )

    def create_decision(self, decision: DecisionRecord) -> DecisionRecord:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO decisions(decision_id, thread_id, payload_json, created_at) VALUES (?, ?, ?, ?)",
                (
                    decision.decision_id,
                    decision.thread_id,
                    json.dumps(_jsonable_decision(decision), ensure_ascii=True, sort_keys=True),
                    decision.created_at,
                ),
            )
            _insert_audit(
                conn,
                ThreadAuditEvent(
                    event_id=f"audit-{decision.decision_id}",
                    thread_id=decision.thread_id,
                    event_type="DECISION_CREATED",
                    actor=decision.decided_by.subject,
                    payload={"decision_type": decision.decision_type.value},
                ),
            )
        return decision

    def export_thread(self, thread_id: str, format: str = "json") -> str | dict[str, Any]:
        thread = self.get_thread(thread_id)
        with sqlite3.connect(self.path) as conn:
            events = _load_audit(conn, thread_id)
        if format == "json":
            return {"thread": thread, "audit_summary": [event.payload for event in events]}
        if format == "md":
            # Minimal markdown export from stored JSON to avoid reconstructing every dataclass.
            lines = [
                f"# {thread.get('title', thread_id)}",
                "",
                f"- Thread ID: `{thread_id}`",
                f"- Status: `{thread.get('status')}`",
                f"- Kind: `{thread.get('kind')}`",
                "",
                "> ANDY Threads MVP local: no attachments, no DM, no real identity provider.",
                "",
            ]
            return "\n".join(lines)
        raise ValueError("unsupported_export_format")

    def search_threads(
        self,
        text: str | None = None,
        reference: AndyThreadReference | None = None,
        status: ThreadStatus | str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if reference is not None:
            clauses.append("reference_key = ?")
            params.append(reference_key(reference))
        if status is not None:
            clauses.append("status = ?")
            params.append(ThreadStatus(status).value)
        sql = "SELECT payload_json FROM threads"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(sql, params).fetchall()
        results = [json.loads(row[0]) for row in rows]
        if text:
            lowered = text.lower()
            results = [item for item in results if lowered in json.dumps(item).lower()]
        return results


def create_thread(path: str | Path, thread: AndyThread) -> AndyThread:
    return ThreadStore(path).create_thread(thread)


def get_thread(path: str | Path, thread_id: str) -> dict[str, Any]:
    return ThreadStore(path).get_thread(thread_id)


def list_threads_by_reference(path: str | Path, reference: AndyThreadReference) -> list[dict[str, Any]]:
    return ThreadStore(path).list_threads_by_reference(reference)


def add_message(path: str | Path, message: ThreadMessage) -> ThreadMessage:
    return ThreadStore(path).add_message(message)


def change_status(path: str | Path, thread_id: str, status: ThreadStatus | str, user_context: ThreadParticipant | Any) -> None:
    ThreadStore(path).change_status(thread_id, status, user_context)


def create_decision(path: str | Path, decision: DecisionRecord) -> DecisionRecord:
    return ThreadStore(path).create_decision(decision)


def export_thread(path: str | Path, thread_id: str, format: str = "json") -> str | dict[str, Any]:
    return ThreadStore(path).export_thread(thread_id, format=format)


def search_threads(
    path: str | Path,
    text: str | None = None,
    reference: AndyThreadReference | None = None,
    status: ThreadStatus | str | None = None,
) -> list[dict[str, Any]]:
    return ThreadStore(path).search_threads(text=text, reference=reference, status=status)


def _insert_audit(conn: sqlite3.Connection, event: ThreadAuditEvent) -> None:
    conn.execute(
        "INSERT INTO audit_events(event_id, thread_id, payload_json, timestamp) VALUES (?, ?, ?, ?)",
        (event.event_id, event.thread_id, json.dumps(_jsonable_audit(event), ensure_ascii=True, sort_keys=True), event.timestamp),
    )


def _load_audit(conn: sqlite3.Connection, thread_id: str) -> list[ThreadAuditEvent]:
    rows = conn.execute("SELECT payload_json FROM audit_events WHERE thread_id = ? ORDER BY timestamp", (thread_id,)).fetchall()
    events: list[ThreadAuditEvent] = []
    for row in rows:
        payload = json.loads(row[0])
        events.append(
            ThreadAuditEvent(
                event_id=payload["event_id"],
                thread_id=payload["thread_id"],
                event_type=payload["event_type"],
                actor=payload["actor"],
                timestamp=payload["timestamp"],
                payload=payload.get("payload", {}),
            )
        )
    return events


def _jsonable_message(message: ThreadMessage) -> dict[str, Any]:
    return {
        "message_id": message.message_id,
        "thread_id": message.thread_id,
        "author": {"subject": message.author.subject, "sector_id": message.author.sector_id},
        "body": message.body,
        "message_kind": message.message_kind.value,
        "created_at": message.created_at,
        "metadata": message.metadata,
    }


def _jsonable_decision(decision: DecisionRecord) -> dict[str, Any]:
    return {
        "decision_id": decision.decision_id,
        "thread_id": decision.thread_id,
        "decision_type": decision.decision_type.value,
        "summary": decision.summary,
        "decided_by": {"subject": decision.decided_by.subject, "sector_id": decision.decided_by.sector_id},
        "evidence_refs": list(decision.evidence_refs),
        "created_at": decision.created_at,
        "metadata": decision.metadata,
    }


def _jsonable_audit(event: ThreadAuditEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "thread_id": event.thread_id,
        "event_type": event.event_type,
        "actor": event.actor,
        "timestamp": event.timestamp,
        "payload": event.payload,
    }
