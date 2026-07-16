from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .references import AndyThreadReference, ThreadEntityType, hash_filter_payload, reference_from_query_filters


def context_from_query_filters(
    filters: Mapping[str, Any] | Any,
    runtime_metadata: Mapping[str, Any] | None = None,
) -> AndyThreadReference:
    metadata = dict(runtime_metadata or {})
    metadata.setdefault("query_signature", build_query_signature(filters))
    return reference_from_query_filters(filters, metadata)


def context_from_export_options(
    export_options: Mapping[str, Any] | Any,
    audit_summary: Mapping[str, Any] | None = None,
) -> AndyThreadReference:
    payload = _mapping_from_object(export_options)
    audit = dict(audit_summary or {})
    return AndyThreadReference(
        entity_type=ThreadEntityType.EXPORT_FILE,
        export_id=str(audit.get("export_id") or compute_filter_hash(payload)[:16]),
        lote_id=_text(audit.get("lote_id")),
        dataset_version=_text(audit.get("dataset_version")),
        filter_hash=compute_filter_hash(payload),
        query_signature=_text(audit.get("query_signature")),
    )


def context_from_bi_selection(selection_payload: Mapping[str, Any]) -> AndyThreadReference:
    payload = dict(selection_payload)
    return AndyThreadReference(
        entity_type=ThreadEntityType.BI_REPORT_PAGE,
        lote_id=_text(payload.get("lote_id")),
        dataset_version=_text(payload.get("dataset_version")),
        report_page=_text(payload.get("report_page")),
        visual_id=_text(payload.get("visual_id")),
        filter_hash=compute_filter_hash(payload),
    )


def compute_filter_hash(payload: Mapping[str, Any]) -> str:
    return hash_filter_payload(_sanitize_payload(payload))


def build_query_signature(filters: Mapping[str, Any] | Any) -> str:
    payload = _mapping_from_object(filters)
    return hashlib.sha256(json.dumps(_sanitize_payload(payload), sort_keys=True, default=str).encode("utf-8")).hexdigest()[:24]


def _mapping_from_object(value: Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "__dict__"):
        return {key: item for key, item in vars(value).items() if not key.startswith("_")}
    return {}


def _sanitize_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        lowered = str(key).lower()
        if lowered in {"dataframe", "df", "frame", "raw_values"}:
            sanitized[key] = "[OMITTED]"
        elif isinstance(value, Mapping):
            sanitized[key] = _sanitize_payload(value)
        elif isinstance(value, (list, tuple, set)):
            sanitized[key] = [str(item) for item in value]
        else:
            sanitized[key] = str(value) if value is not None else None
    return sanitized


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
