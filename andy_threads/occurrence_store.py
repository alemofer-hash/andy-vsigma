from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .audit import redact_audit_payload
from .models import ThreadAuditEvent, ThreadParticipant
from .notification_intent import NotificationIntent, notification_intent_from_dict, notification_intent_to_dict
from .occurrences import Occurrence, OccurrenceStatus, occurrence_public_summary
from .references import AndyThreadReference, reference_key, reference_public_summary
from .sector_lens import SectorId


OCCURRENCE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS occurrences (
    occurrence_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    reference_key TEXT NOT NULL,
    status TEXT NOT NULL,
    owner_sector TEXT NOT NULL,
    target_sector TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS occurrence_audit_events (
    event_id TEXT PRIMARY KEY,
    occurrence_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notification_intents (
    intent_id TEXT PRIMARY KEY,
    occurrence_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL,
    target_sector TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def initialize_occurrence_store(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(target) as conn:
        conn.executescript(OCCURRENCE_SCHEMA_SQL)
    return target


class OccurrenceStore:
    def __init__(self, path: str | Path) -> None:
        self.path = initialize_occurrence_store(path)

    def create_occurrence(self, occurrence: Occurrence) -> Occurrence:
        payload = occurrence_to_dict(occurrence)
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT INTO occurrences(
                    occurrence_id, thread_id, payload_json, reference_key, status,
                    owner_sector, target_sector, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _occurrence_row(occurrence, payload),
            )
            _insert_occurrence_audit(
                conn,
                occurrence,
                "OCCURRENCE_CREATED",
                occurrence.created_by.subject,
                {"reference_key": occurrence.reference_key, "status": occurrence.status.value},
            )
        return occurrence

    def get_occurrence(self, occurrence_id: str) -> dict[str, Any]:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute(
                "SELECT payload_json FROM occurrences WHERE occurrence_id = ?",
                (occurrence_id,),
            ).fetchone()
        if not row:
            raise KeyError(occurrence_id)
        return json.loads(row[0])

    def update_occurrence(self, occurrence: Occurrence, *, actor: ThreadParticipant, event_type: str = "OCCURRENCE_UPDATED") -> Occurrence:
        payload = occurrence_to_dict(occurrence)
        with sqlite3.connect(self.path) as conn:
            updated = conn.execute(
                """
                UPDATE occurrences
                SET thread_id = ?, payload_json = ?, reference_key = ?, status = ?,
                    owner_sector = ?, target_sector = ?, created_at = ?, updated_at = ?
                WHERE occurrence_id = ?
                """,
                (
                    occurrence.thread_id,
                    json.dumps(payload, ensure_ascii=True, sort_keys=True),
                    occurrence.reference_key,
                    occurrence.status.value,
                    occurrence.owner_sector.value,
                    occurrence.target_sector.value if occurrence.target_sector is not None else None,
                    occurrence.created_at,
                    occurrence.updated_at,
                    occurrence.occurrence_id,
                ),
            ).rowcount
            if updated == 0:
                raise KeyError(occurrence.occurrence_id)
            _insert_occurrence_audit(
                conn,
                occurrence,
                event_type,
                actor.subject,
                {"status": occurrence.status.value, "target_sector": _sector_value(occurrence.target_sector)},
            )
        return occurrence

    def change_status(
        self,
        occurrence: Occurrence,
        status: OccurrenceStatus | str,
        *,
        actor: ThreadParticipant,
        target_sector: SectorId | str | None = None,
        closure_reason: str | None = None,
        evidence_refs: tuple[str, ...] | None = None,
        decision_refs: tuple[str, ...] | None = None,
    ) -> Occurrence:
        updated = occurrence.transition(
            status,
            actor=actor,
            target_sector=target_sector,
            closure_reason=closure_reason,
            evidence_refs=evidence_refs,
            decision_refs=decision_refs,
        )
        return self.update_occurrence(updated, actor=actor, event_type="OCCURRENCE_STATUS_CHANGED")

    def list_occurrences(
        self,
        *,
        reference: AndyThreadReference | None = None,
        status: OccurrenceStatus | str | None = None,
        owner_sector: SectorId | str | None = None,
        target_sector: SectorId | str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if reference is not None:
            clauses.append("reference_key = ?")
            params.append(reference_key(reference))
        if status is not None:
            clauses.append("status = ?")
            params.append(OccurrenceStatus(status).value)
        if owner_sector is not None:
            clauses.append("owner_sector = ?")
            params.append(SectorId(owner_sector).value)
        if target_sector is not None:
            clauses.append("target_sector = ?")
            params.append(SectorId(target_sector).value)
        sql = "SELECT payload_json FROM occurrences"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at"
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [json.loads(row[0]) for row in rows]

    def create_notification_intent(self, intent: NotificationIntent, *, actor: str) -> NotificationIntent:
        payload = notification_intent_to_dict(intent)
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT INTO notification_intents(
                    intent_id, occurrence_id, payload_json, status, target_sector, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    intent.intent_id,
                    intent.occurrence_id,
                    json.dumps(payload, ensure_ascii=True, sort_keys=True),
                    intent.status.value,
                    intent.target_sector.value,
                    intent.created_at,
                ),
            )
            occurrence_payload = self._get_occurrence_payload(conn, intent.occurrence_id)
            _insert_notification_audit(
                conn,
                intent,
                "NOTIFICATION_INTENT_CREATED",
                actor,
                {"status": intent.status.value, "target_sector": intent.target_sector.value},
                occurrence_payload=occurrence_payload,
            )
        return intent

    def get_notification_intent(self, intent_id: str) -> dict[str, Any]:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute(
                "SELECT payload_json FROM notification_intents WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()
        if not row:
            raise KeyError(intent_id)
        return json.loads(row[0])

    def list_notification_intents(self, occurrence_id: str) -> list[dict[str, Any]]:
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                "SELECT payload_json FROM notification_intents WHERE occurrence_id = ? ORDER BY created_at",
                (occurrence_id,),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def export_occurrence(self, occurrence_id: str, format: str = "json") -> str | dict[str, Any]:
        occurrence = self.get_occurrence(occurrence_id)
        intents = self.list_notification_intents(occurrence_id)
        with sqlite3.connect(self.path) as conn:
            audits = _load_occurrence_audit(conn, occurrence_id)
        if format == "json":
            return {"occurrence": occurrence, "notification_intents": intents, "audit_summary": audits}
        if format == "md":
            lines = [
                f"# {occurrence.get('title', occurrence_id)}",
                "",
                f"- Occurrence ID: `{occurrence_id}`",
                f"- Thread ID: `{occurrence.get('thread_id')}`",
                f"- Status: `{occurrence.get('status')}`",
                f"- Severity: `{occurrence.get('severity')}`",
                f"- Problem domain: `{occurrence.get('problem_domain')}`",
                f"- Reference: `{occurrence.get('reference_key')}`",
                "",
                "> ANDY Occurrences MVP local: notification intents only; no real provider send.",
                "",
            ]
            return "\n".join(lines)
        raise ValueError("unsupported_export_format")

    @staticmethod
    def _get_occurrence_payload(conn: sqlite3.Connection, occurrence_id: str) -> dict[str, Any]:
        row = conn.execute("SELECT payload_json FROM occurrences WHERE occurrence_id = ?", (occurrence_id,)).fetchone()
        if not row:
            raise KeyError(occurrence_id)
        return json.loads(row[0])


def occurrence_to_dict(occurrence: Occurrence) -> dict[str, Any]:
    payload = occurrence_public_summary(occurrence)
    payload.update(
        {
            "summary": occurrence.summary,
            "reference": reference_public_summary(occurrence.reference),
            "created_by": {
                "subject": occurrence.created_by.subject,
                "sector_id": occurrence.created_by.sector_id,
            },
            "closure_reason": occurrence.closure_reason,
            "evidence_refs": list(occurrence.evidence_refs),
            "decision_refs": list(occurrence.decision_refs),
            "tags": list(occurrence.tags),
            "metadata": redact_audit_payload(occurrence.metadata),
            "mvp_notice": "ANDY Occurrences local MVP; notification intents only; no real provider send.",
        }
    )
    return payload


def _occurrence_row(occurrence: Occurrence, payload: dict[str, Any]) -> tuple[Any, ...]:
    return (
        occurrence.occurrence_id,
        occurrence.thread_id,
        json.dumps(payload, ensure_ascii=True, sort_keys=True),
        occurrence.reference_key,
        occurrence.status.value,
        occurrence.owner_sector.value,
        occurrence.target_sector.value if occurrence.target_sector is not None else None,
        occurrence.created_at,
        occurrence.updated_at,
    )


def _insert_occurrence_audit(
    conn: sqlite3.Connection,
    occurrence: Occurrence,
    event_type: str,
    actor: str,
    payload: dict[str, Any],
) -> None:
    event = ThreadAuditEvent(
        event_id=f"audit-{occurrence.occurrence_id}-{event_type}-{occurrence.updated_at}",
        thread_id=occurrence.thread_id,
        event_type=event_type,
        actor=actor,
        timestamp=occurrence.updated_at,
        payload=redact_audit_payload(payload),
    )
    conn.execute(
        "INSERT OR REPLACE INTO occurrence_audit_events(event_id, occurrence_id, payload_json, timestamp) VALUES (?, ?, ?, ?)",
        (
            event.event_id,
            occurrence.occurrence_id,
            json.dumps(_jsonable_audit(event), ensure_ascii=True, sort_keys=True),
            event.timestamp,
        ),
    )


def _insert_notification_audit(
    conn: sqlite3.Connection,
    intent: NotificationIntent,
    event_type: str,
    actor: str,
    payload: dict[str, Any],
    *,
    occurrence_payload: dict[str, Any],
) -> None:
    event = ThreadAuditEvent(
        event_id=f"audit-{intent.intent_id}-{event_type}",
        thread_id=str(occurrence_payload.get("thread_id", intent.occurrence_id)),
        event_type=event_type,
        actor=actor,
        timestamp=intent.created_at,
        payload=redact_audit_payload(payload),
    )
    conn.execute(
        "INSERT OR REPLACE INTO occurrence_audit_events(event_id, occurrence_id, payload_json, timestamp) VALUES (?, ?, ?, ?)",
        (
            event.event_id,
            intent.occurrence_id,
            json.dumps(_jsonable_audit(event), ensure_ascii=True, sort_keys=True),
            event.timestamp,
        ),
    )


def _load_occurrence_audit(conn: sqlite3.Connection, occurrence_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT payload_json FROM occurrence_audit_events WHERE occurrence_id = ? ORDER BY timestamp",
        (occurrence_id,),
    ).fetchall()
    return [json.loads(row[0]) for row in rows]


def _jsonable_audit(event: ThreadAuditEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "thread_id": event.thread_id,
        "event_type": event.event_type,
        "actor": event.actor,
        "timestamp": event.timestamp,
        "payload": event.payload,
    }


def _sector_value(value: SectorId | None) -> str | None:
    return value.value if value is not None else None


def notification_intent_from_stored_dict(payload: dict[str, Any]) -> NotificationIntent:
    return notification_intent_from_dict(payload)
