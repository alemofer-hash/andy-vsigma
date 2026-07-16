from __future__ import annotations

import datetime as dt
import math
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

import pandas as pd

from desktop_app.models import DesktopRuntimeState, ExportAuditResult, ExportOptions, PageResult, QueryFilters


BOUNDARY_SCHEMA = "andy.vsigma.boundary"
BOUNDARY_SCHEMA_VERSION = 1


def _is_nullish(value: Any) -> bool:
    if value is None:
        return True
    try:
        result = pd.isna(value)
    except Exception:
        return False
    if isinstance(result, bool):
        return result
    return False


def _normalize_scalar(value: Any) -> Any:
    if _is_nullish(value):
        return None
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        if isinstance(value, dt.datetime):
            return value.replace(tzinfo=None).isoformat(timespec="seconds")
        return value.isoformat()
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)
    return value


def normalize_boundary_value(value: Any) -> Any:
    if is_dataclass(value):
        return normalize_boundary_value(asdict(value))
    if isinstance(value, Mapping):
        return {str(k): normalize_boundary_value(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [normalize_boundary_value(v) for v in value]
    if isinstance(value, list):
        return [normalize_boundary_value(v) for v in value]
    if isinstance(value, pd.DataFrame):
        return frame_to_boundary_payload(value)
    return _normalize_scalar(value)


def _infer_column_kind(series: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_integer_dtype(series):
        return "integer"
    if pd.api.types.is_float_dtype(series):
        return "number"
    return "string"


def frame_to_boundary_payload(frame: pd.DataFrame) -> Dict[str, Any]:
    safe_frame = frame.copy()
    columns = [
        {"name": str(column), "kind": _infer_column_kind(safe_frame[column])}
        for column in safe_frame.columns
    ]
    rows = [
        {str(column): normalize_boundary_value(value) for column, value in row.items()}
        for row in safe_frame.to_dict(orient="records")
    ]
    return {"columns": columns, "rows": rows}


def boundary_envelope(kind: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema": BOUNDARY_SCHEMA,
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "kind": str(kind),
        "payload": normalize_boundary_value(dict(payload)),
    }


def query_filters_payload(filters: QueryFilters) -> Dict[str, Any]:
    return normalize_boundary_value(filters)


def export_options_payload(options: ExportOptions) -> Dict[str, Any]:
    return normalize_boundary_value(options)


def runtime_state_payload(state: DesktopRuntimeState) -> Dict[str, Any]:
    return normalize_boundary_value(state)


def page_result_payload(page: PageResult) -> Dict[str, Any]:
    return {
        "total": int(page.total),
        "frame": frame_to_boundary_payload(page.frame),
    }


def export_audit_payload(result: ExportAuditResult) -> Dict[str, Any]:
    findings = []
    for finding in result.findings:
        if is_dataclass(finding):
            findings.append(normalize_boundary_value(finding))
        elif isinstance(finding, Mapping):
            findings.append(normalize_boundary_value(finding))
        else:
            findings.append(
                {
                    "code": str(getattr(finding, "code", "")),
                    "severity": str(getattr(finding, "severity", "")),
                    "title": str(getattr(finding, "title", "")),
                    "hard_stop": bool(getattr(finding, "hard_stop", False)),
                }
            )
    return {
        "status": str(result.status),
        "metrics": normalize_boundary_value(result.metrics),
        "findings": findings,
    }


def sample_boundary_payloads() -> Dict[str, Any]:
    filters = QueryFilters(
        anos_sel=[2026],
        meses_sel=[3],
        dias_sel=["2026-03-19"],
        se_sel=["SE1"],
        bay_sel=["B1"],
        equipamento_sel=["EQ1"],
        terminal_sel=["T1"],
        vars_sel=["IA", "IB"],
        ponto_id_like="EQ1",
    )
    options = ExportOptions(
        fmt="xlsx_dashboard",
        agg="max",
        time_floor="15min",
        max_timestamps=100_000,
        equip_slots=8,
        var_slots=6,
        destination_excel=True,
        split_timestamp_columns_xlsx=True,
    )
    page = PageResult(
        total=2,
        frame=pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2026-03-19 14:45:12", "2026-03-19 15:00:00"]),
                "SE": ["SE1", "SE1"],
                "BAY": ["B1", "B1"],
                "EQUIPAMENTO": ["EQ1", "EQ1"],
                "TERMINAL": ["T1", "T1"],
                "ponto_id": ["SE1|B1|EQ1|T1", "SE1|B1|EQ1|T1"],
                "equip_id": ["EQ1", "EQ1"],
                "var": ["IA", "IB"],
                "classe": ["analog", "analog"],
                "valor": [10.5, 11.0],
            }
        ),
    )
    audit = ExportAuditResult(
        status="OK",
        metrics={"rows_estimated": 2, "n_equips": 1, "n_vars": 2},
        findings=[],
    )
    return {
        "query_filters": boundary_envelope("query_filters", query_filters_payload(filters)),
        "export_options": boundary_envelope("export_options", export_options_payload(options)),
        "page_result": boundary_envelope("page_result", page_result_payload(page)),
        "export_audit": boundary_envelope("export_audit", export_audit_payload(audit)),
    }


def all_boundary_payloads_are_json_objects(payloads: Iterable[Mapping[str, Any]]) -> bool:
    return all(isinstance(payload, Mapping) for payload in payloads)
