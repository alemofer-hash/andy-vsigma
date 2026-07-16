from __future__ import annotations

import datetime as dt
import json
import os
from typing import Any


def _safe_filter_repr(filters: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in filters.items():
        if isinstance(value, str):
            text = value.strip()
            out[key] = (text[:64] + "...") if len(text) > 64 else text
        elif isinstance(value, list):
            out[key] = [str(v)[:32] for v in value[:20]]
        else:
            out[key] = value
    return out


def _json_safe(value: Any) -> Any:
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def audit_export(
    *,
    user_id: str,
    role: str,
    rowcount: int,
    filters: dict[str, Any],
    file_path: str,
    audit_log_path: str | None = None,
) -> None:
    event = {
        "event": "export",
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "user_id": str(user_id or "unknown")[:64],
        "role": str(role or "unknown")[:32],
        "rowcount": int(rowcount),
        "filters": _safe_filter_repr(filters),
        "file_name": os.path.basename(file_path),
    }
    _write_event(event, audit_log_path=audit_log_path)


def _write_event(event: dict[str, Any], audit_log_path: str | None = None) -> None:
    line = json.dumps(_json_safe(event), ensure_ascii=True, default=str)
    if audit_log_path:
        os.makedirs(os.path.dirname(audit_log_path), exist_ok=True)
        with open(audit_log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    else:
        print(line)


def audit_export_risk(
    *,
    user_id: str,
    role: str,
    intent: dict[str, Any],
    filters: dict[str, Any],
    metrics: dict[str, Any],
    findings: list[dict[str, Any]],
    action_taken: str | None = None,
    audit_log_path: str | None = None,
) -> None:
    event = {
        "event": "export_audit",
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "user_id": str(user_id or "unknown")[:64],
        "role": str(role or "unknown")[:32],
        "intent": _safe_filter_repr(intent),
        "filters": _safe_filter_repr(filters),
        "metrics": _safe_filter_repr(metrics),
        "findings": findings[:30],
        "action_taken": str(action_taken or "")[:64],
    }
    _write_event(event, audit_log_path=audit_log_path)


def read_recent_audit_events(
    *,
    audit_log_path: str | None,
    event_type: str = "export_audit",
    limit: int = 20,
) -> list[dict[str, Any]]:
    if not audit_log_path or not os.path.exists(audit_log_path):
        return []
    lines: list[str] = []
    with open(audit_log_path, "r", encoding="utf-8") as f:
        for line in f:
            txt = line.strip()
            if txt:
                lines.append(txt)
    out: list[dict[str, Any]] = []
    for txt in reversed(lines):
        try:
            obj = json.loads(txt)
        except json.JSONDecodeError:
            continue
        if str(obj.get("event")) != event_type:
            continue
        out.append(obj)
        if len(out) >= limit:
            break
    return out
