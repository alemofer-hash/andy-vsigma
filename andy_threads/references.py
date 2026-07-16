from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping


class ThreadEntityType(str, Enum):
    DATASET_LOTE = "DATASET_LOTE"
    MEASUREMENT_POINT = "MEASUREMENT_POINT"
    SUBSTATION = "SUBSTATION"
    FEEDER = "FEEDER"
    EQUIPMENT = "EQUIPMENT"
    TERMINAL = "TERMINAL"
    VARIABLE = "VARIABLE"
    PERIOD = "PERIOD"
    POWER_FLOW_EVENT = "POWER_FLOW_EVENT"
    PATAMAR_ANALYSIS = "PATAMAR_ANALYSIS"
    QUALITY_FLAG = "QUALITY_FLAG"
    EXPORT_FILE = "EXPORT_FILE"
    BI_REPORT_PAGE = "BI_REPORT_PAGE"
    DASHBOARD_SNAPSHOT = "DASHBOARD_SNAPSHOT"
    PARITY_CHECK = "PARITY_CHECK"


@dataclass(frozen=True)
class AndyThreadReference:
    entity_type: ThreadEntityType | str
    lote_id: str | None = None
    dataset_version: str | None = None
    source_fingerprint: str | None = None
    se: str | None = None
    bay: str | None = None
    alimentador: str | None = None
    bay_or_feeder: str | None = None
    equipamento: str | None = None
    terminal: str | None = None
    variavel: str | None = None
    ponto_id: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    source_cadence: str | None = None
    filter_hash: str | None = None
    query_signature: str | None = None
    report_page: str | None = None
    visual_id: str | None = None
    export_id: str | None = None
    quality_flag: str | None = None
    anomaly_id: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.entity_type, str):
            object.__setattr__(self, "entity_type", ThreadEntityType(self.entity_type))


IDENTIFIER_FIELDS = (
    "lote_id",
    "dataset_version",
    "source_fingerprint",
    "se",
    "bay",
    "alimentador",
    "bay_or_feeder",
    "equipamento",
    "terminal",
    "variavel",
    "ponto_id",
    "filter_hash",
    "query_signature",
    "report_page",
    "visual_id",
    "export_id",
    "quality_flag",
    "anomaly_id",
)


def hash_filter_payload(payload: Mapping[str, Any]) -> str:
    safe_payload = _to_jsonable(payload)
    encoded = json.dumps(safe_payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def reference_key(ref: AndyThreadReference) -> str:
    summary = reference_public_summary(ref)
    digest = hash_filter_payload(summary)[:16]
    return f"{ref.entity_type.value}:{digest}"


def validate_reference(ref: AndyThreadReference) -> list[str]:
    failures: list[str] = []
    if not ref.entity_type:
        failures.append("entity_type_required")
    if bool(ref.period_start) != bool(ref.period_end):
        failures.append("period_start_and_period_end_required_together")
    has_identifier = any(_has_text(getattr(ref, field)) for field in IDENTIFIER_FIELDS)
    if ref.entity_type == ThreadEntityType.PERIOD and ref.period_start and ref.period_end:
        has_identifier = True
    if not has_identifier:
        failures.append("technical_identifier_required")
    return failures


def reference_public_summary(ref: AndyThreadReference) -> dict[str, Any]:
    payload = asdict(ref)
    payload["entity_type"] = ref.entity_type.value
    return {key: value for key, value in payload.items() if value not in (None, "", [], {})}


def reference_from_query_filters(
    filters: Mapping[str, Any] | Any,
    metadata: Mapping[str, Any] | None = None,
) -> AndyThreadReference:
    payload = _mapping_from_object(filters)
    meta = dict(metadata or {})
    filter_hash = hash_filter_payload(payload)
    se = _first(payload.get("se_sel") or payload.get("se"))
    bay_or_feeder = _first(payload.get("bay_sel") or payload.get("bay") or payload.get("alimentador"))
    equipamento = _first(payload.get("equipamento_sel") or payload.get("equipamento"))
    terminal = _first(payload.get("terminal_sel") or payload.get("terminal"))
    variavel = _first(payload.get("vars_sel") or payload.get("variavel"))
    source_cadence = _first(payload.get("source_cadence_sel") or payload.get("source_cadence"))
    year = _first(payload.get("anos_sel") or payload.get("ano"))
    entity_type = ThreadEntityType.MEASUREMENT_POINT
    if meta.get("entity_type"):
        entity_type = ThreadEntityType(str(meta["entity_type"]))
    elif se and not any((bay_or_feeder, equipamento, terminal, variavel)):
        entity_type = ThreadEntityType.SUBSTATION
    elif bay_or_feeder and not any((equipamento, terminal, variavel)):
        entity_type = ThreadEntityType.FEEDER
    elif equipamento and not terminal:
        entity_type = ThreadEntityType.EQUIPMENT
    elif terminal and not variavel:
        entity_type = ThreadEntityType.TERMINAL
    elif variavel:
        entity_type = ThreadEntityType.VARIABLE

    return AndyThreadReference(
        entity_type=entity_type,
        lote_id=_text(meta.get("lote_id")),
        dataset_version=_text(meta.get("dataset_version")),
        source_fingerprint=_text(meta.get("source_fingerprint")),
        se=_text(se),
        bay_or_feeder=_text(bay_or_feeder),
        equipamento=_text(equipamento),
        terminal=_text(terminal),
        variavel=_text(variavel),
        ponto_id=_text(payload.get("ponto_id") or meta.get("ponto_id")),
        period_start=_text(meta.get("period_start") or year),
        period_end=_text(meta.get("period_end") or year),
        source_cadence=_text(source_cadence),
        filter_hash=filter_hash,
        query_signature=_text(meta.get("query_signature")),
        quality_flag=_text(meta.get("quality_flag")),
        anomaly_id=_text(meta.get("anomaly_id")),
    )


def _mapping_from_object(value: Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "__dict__"):
        return {key: _to_jsonable(item) for key, item in vars(value).items() if not key.startswith("_")}
    return {}


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _first(value: Any) -> Any:
    if isinstance(value, (list, tuple, set)):
        for item in value:
            if _has_text(item):
                return item
        return None
    return value


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _has_text(value: Any) -> bool:
    return _text(value) is not None
