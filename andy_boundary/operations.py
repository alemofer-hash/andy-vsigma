from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Mapping

from desktop_app.export_service import DesktopExportService
from desktop_app.models import DesktopRuntimeState, ExportOptions, QueryFilters
from desktop_app.query_service import DesktopQueryService
from desktop_app.runtime import DesktopRuntimeService
from andy_bi.enforcement import enforce_boundary_policy

from andy_boundary.contracts import (
    BOUNDARY_SCHEMA,
    BOUNDARY_SCHEMA_VERSION,
    boundary_envelope,
    export_audit_payload,
    export_options_payload,
    page_result_payload,
    query_filters_payload,
    runtime_state_payload,
)


BOUNDARY_REQUEST_SCHEMA = "andy.vsigma.boundary.request"
SUPPORTED_OPERATIONS = frozenset({"runtime.load_state", "query.page", "export.audit", "export.csv_long"})


class BoundaryOperationError(ValueError):
    pass


def _payload(request: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = request.get("payload", {})
    if not isinstance(payload, Mapping):
        raise BoundaryOperationError("Request payload must be an object.")
    return payload


def _require_str(payload: Mapping[str, Any], key: str) -> str:
    value = str(payload.get(key, "")).strip()
    if not value:
        raise BoundaryOperationError(f"Missing required payload field: {key}")
    return value


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "sim"}:
        return True
    if text in {"0", "false", "no", "n", "nao", "não"}:
        return False
    return default


def _as_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    return [str(value)]


def _as_int_list(value: Any) -> list[int]:
    out: list[int] = []
    raw = value if isinstance(value, (list, tuple)) else ([] if value is None else [value])
    for item in raw:
        try:
            out.append(int(item))
        except Exception:
            continue
    return out


def _query_filters_from_payload(payload: Mapping[str, Any]) -> QueryFilters:
    advanced_equals_raw = payload.get("advanced_equals", {})
    advanced_ranges_raw = payload.get("advanced_ranges", {})
    advanced_equals = {
        str(key): _as_str_list(value)
        for key, value in dict(advanced_equals_raw if isinstance(advanced_equals_raw, Mapping) else {}).items()
    }
    advanced_ranges: dict[str, tuple[float, float]] = {}
    for key, value in dict(advanced_ranges_raw if isinstance(advanced_ranges_raw, Mapping) else {}).items():
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            continue
        try:
            advanced_ranges[str(key)] = (float(value[0]), float(value[1]))
        except Exception:
            continue

    ano_raw = payload.get("ano")
    try:
        ano = int(ano_raw) if ano_raw is not None else None
    except Exception:
        ano = None

    return QueryFilters(
        ano=ano,
        anos_sel=_as_int_list(payload.get("anos_sel")),
        meses_sel=_as_int_list(payload.get("meses_sel")),
        dias_sel=_as_str_list(payload.get("dias_sel")),
        se_sel=_as_str_list(payload.get("se_sel")),
        bay_sel=_as_str_list(payload.get("bay_sel")),
        equipamento_sel=_as_str_list(payload.get("equipamento_sel")),
        terminal_sel=_as_str_list(payload.get("terminal_sel")),
        vars_sel=_as_str_list(payload.get("vars_sel")),
        ponto_id_like=str(payload.get("ponto_id_like", "") or ""),
        advanced_equals=advanced_equals,
        advanced_ranges=advanced_ranges,
    )


def _export_options_from_payload(payload: Mapping[str, Any]) -> ExportOptions:
    limit_raw = payload.get("limit_cap")
    try:
        limit_cap = int(limit_raw) if limit_raw is not None else None
    except Exception:
        limit_cap = None
    return ExportOptions(
        fmt=str(payload.get("fmt", "csv_long") or "csv_long"),
        limit_cap=limit_cap,
        agg=str(payload.get("agg", "max") or "max"),
        time_floor=(str(payload.get("time_floor", "")).strip() or None),
        max_timestamps=_as_int(payload.get("max_timestamps"), default=100_000),
        equip_slots=_as_int(payload.get("equip_slots"), default=8),
        var_slots=_as_int(payload.get("var_slots"), default=6),
        destination_excel=_as_bool(payload.get("destination_excel"), default=True),
        split_timestamp_columns=_as_bool(payload.get("split_timestamp_columns"), default=False),
        split_timestamp_columns_xlsx=_as_bool(payload.get("split_timestamp_columns_xlsx"), default=False),
    )


def _minimal_runtime_state(*, db_path: str, root: Path) -> DesktopRuntimeState:
    exports = (root / "exports").resolve()
    audit_log_path = (root / "logs" / "audit.jsonl").resolve()
    return DesktopRuntimeState(
        layout={"exports": exports, "audit_log_path": audit_log_path},
        settings={"export_dir": str(exports)},
        source_root="",
        source_reason="boundary_request",
        source_mode="configured",
        source_exists=False,
        source_is_unc=False,
        source_file_count=0,
        source_ready_for_indexing=False,
        source_status_message="boundary request",
        db_path=str(db_path),
        db_exists=Path(db_path).exists(),
        setup_required=False,
        settings_path=str((root / "config" / "settings.json").resolve()),
        last_index={},
        shared_catalog_root="",
        shared_catalog_reason="",
        shared_catalog_enabled=False,
        shared_catalog_exists=False,
        shared_snapshot={},
        shared_catalog_latest={},
    )


def _operation_runtime_load_state(payload: Mapping[str, Any]) -> Dict[str, Any]:
    root_text = str(payload.get("root", "")).strip()
    root = Path(root_text).resolve() if root_text else None
    service = DesktopRuntimeService(root=root)
    state = service.load_state(bootstrap_if_ready=_as_bool(payload.get("bootstrap_if_ready"), default=False))
    return boundary_envelope("runtime_state", runtime_state_payload(state))


def _operation_query_page(payload: Mapping[str, Any]) -> Dict[str, Any]:
    db_path = _require_str(payload, "db_path")
    filters_payload = payload.get("filters", {})
    if not isinstance(filters_payload, Mapping):
        raise BoundaryOperationError("query.page filters must be an object.")
    enforce_boundary_policy("query.page", payload)
    service = DesktopQueryService(db_path)
    service.validate_ready()
    page = service.query_page(
        filters=_query_filters_from_payload(filters_payload),
        page_size=_as_int(payload.get("page_size"), default=100),
        page_number=_as_int(payload.get("page_number"), default=1),
        order_label=str(payload.get("order_label", "timestamp ASC") or "timestamp ASC"),
    )
    return boundary_envelope("page_result", page_result_payload(page))


def _operation_export_audit(payload: Mapping[str, Any]) -> Dict[str, Any]:
    db_path = _require_str(payload, "db_path")
    filters_payload = payload.get("filters", {})
    options_payload = payload.get("options", {})
    if not isinstance(filters_payload, Mapping):
        raise BoundaryOperationError("export.audit filters must be an object.")
    if not isinstance(options_payload, Mapping):
        raise BoundaryOperationError("export.audit options must be an object.")
    enforce_boundary_policy("export.audit", payload)
    root_text = str(payload.get("runtime_root", "")).strip()
    root = Path(root_text).resolve() if root_text else Path(db_path).resolve().parent
    query_service = DesktopQueryService(db_path)
    query_service.validate_ready()
    runtime_state = _minimal_runtime_state(db_path=db_path, root=root)
    result = DesktopExportService(runtime_state).audit(
        query_service,
        _query_filters_from_payload(filters_payload),
        _export_options_from_payload(options_payload),
    )
    return boundary_envelope("export_audit", export_audit_payload(result))


def _operation_export_csv_long(payload: Mapping[str, Any]) -> Dict[str, Any]:
    db_path = _require_str(payload, "db_path")
    enforce_boundary_policy("export.csv_long", payload)
    filters_payload = payload.get("filters", {})
    if not isinstance(filters_payload, Mapping):
        filters_payload = {}
    root_text = str(payload.get("runtime_root", "")).strip()
    root = Path(root_text).resolve() if root_text else Path(db_path).resolve().parent
    output_path = str(payload.get("output_path", "")).strip() or str((root / "exports" / "sentinela_export_long.csv").resolve())
    query_service = DesktopQueryService(db_path)
    query_service.validate_ready()
    runtime_state = _minimal_runtime_state(db_path=db_path, root=root)
    out_file = DesktopExportService(runtime_state).export_csv_long(
        query_service,
        _query_filters_from_payload(filters_payload),
        output_path=output_path,
    )
    return boundary_envelope("export_result", {"path": out_file, "format": "csv_long"})


_HANDLERS: dict[str, Callable[[Mapping[str, Any]], Dict[str, Any]]] = {
    "runtime.load_state": _operation_runtime_load_state,
    "query.page": _operation_query_page,
    "export.audit": _operation_export_audit,
    "export.csv_long": _operation_export_csv_long,
}


def execute_boundary_request(request: Mapping[str, Any]) -> Dict[str, Any]:
    if str(request.get("schema", "")).strip() not in {"", BOUNDARY_REQUEST_SCHEMA}:
        raise BoundaryOperationError("Unsupported request schema.")
    operation = str(request.get("operation", "")).strip()
    if operation not in SUPPORTED_OPERATIONS:
        raise BoundaryOperationError(f"Unsupported operation: {operation}")
    return _HANDLERS[operation](_payload(request))


def error_envelope(operation: str, exc: BaseException) -> Dict[str, Any]:
    return {
        "schema": BOUNDARY_SCHEMA,
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "kind": "error",
        "payload": {
            "operation": str(operation or ""),
            "error_type": exc.__class__.__name__,
            "message": str(exc),
        },
    }


def make_boundary_request(operation: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema": BOUNDARY_REQUEST_SCHEMA,
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "operation": str(operation),
        "payload": {
            **dict(payload),
            **(
                {"filters": query_filters_payload(payload["filters"])}
                if isinstance(payload.get("filters"), QueryFilters)
                else {}
            ),
            **(
                {"options": export_options_payload(payload["options"])}
                if isinstance(payload.get("options"), ExportOptions)
                else {}
            ),
        },
    }
