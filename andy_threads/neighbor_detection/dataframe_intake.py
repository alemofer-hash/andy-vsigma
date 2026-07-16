from __future__ import annotations

from typing import Iterable

import pandas as pd

from .key_parser import is_feeder_name, parse_andy_key
from .models import CURRENT_VARIABLES, FeederProfile, stable_hash
from .workbook_intake import normalize_current_variables, profile_feeders


def frame_from_dashboard_agg(
    df_agg: pd.DataFrame,
    *,
    source_alias: str,
    current_variables: Iterable[object] | None = None,
) -> tuple[pd.DataFrame, dict[str, object], list[FeederProfile]]:
    selected_vars = set(normalize_current_variables(current_variables))
    if df_agg.empty:
        manifest = _manifest(source_alias=source_alias, rows=0, current_rows=0, selected_vars=selected_vars)
        return pd.DataFrame(), manifest, []

    required = {"_TS", "_KEY", "_VAL", "_SE", "_BAY", "_EQUIP", "_TERMINAL", "_VAR", "_CLASSE"}
    missing = sorted(required.difference(df_agg.columns))
    if missing:
        raise ValueError("neighbor_detection_dashboard_schema_missing:" + ",".join(missing))

    records: list[dict[str, object]] = []
    parse_errors = 0
    var_counts = df_agg["_VAR"].fillna("").astype(str).str.upper().value_counts().to_dict()
    source_hash = stable_hash(
        {
            "source_alias": source_alias,
            "rows": int(len(df_agg.index)),
            "ts_min": str(pd.to_datetime(df_agg["_TS"], errors="coerce").min()),
            "ts_max": str(pd.to_datetime(df_agg["_TS"], errors="coerce").max()),
            "vars": sorted(str(value) for value in df_agg["_VAR"].dropna().astype(str).unique()),
        },
        length=32,
    )

    for row in df_agg.to_dict(orient="records"):
        raw_var = str(row.get("_VAR") or "").strip().upper()
        if raw_var not in selected_vars or raw_var not in CURRENT_VARIABLES:
            continue
        raw_key = str(row.get("_KEY") or "").strip()
        try:
            parsed = parse_andy_key(raw_key)
        except ValueError:
            parse_errors += 1
            parsed = None
        if parsed is not None and parsed.variable.upper() in selected_vars:
            se = parsed.se
            feeder = parsed.feeder
            equipment = parsed.equipment
            terminal = parsed.terminal
            variable = parsed.variable.upper()
            key = parsed.canonical
        else:
            se = str(row.get("_SE") or "").strip()
            feeder = str(row.get("_BAY") or "").strip()
            equipment = str(row.get("_EQUIP") or "").strip()
            terminal = str(row.get("_TERMINAL") or "").strip()
            variable = raw_var
            key = "|".join((se, feeder, equipment, terminal, variable))
        try:
            value = float(row.get("_VAL"))
        except (TypeError, ValueError):
            value = float("nan")
        records.append(
            {
                "source_alias": source_alias,
                "source_hash": source_hash,
                "timestamp": pd.to_datetime(row.get("_TS"), errors="coerce"),
                "key": key,
                "se": se,
                "feeder": feeder,
                "equipment": equipment,
                "terminal": terminal,
                "variable": variable,
                "value": value,
                "raw_equip": equipment,
                "classe": row.get("_CLASSE"),
                "tskey": f"{row.get('_TS')}|{key}",
                "is_feeder": is_feeder_name(feeder),
            }
        )

    frame = pd.DataFrame.from_records(records)
    if not frame.empty:
        frame = frame.dropna(subset=["timestamp"]).sort_values(["se", "variable", "feeder", "timestamp"]).reset_index(drop=True)
    manifest = _manifest(
        source_alias=source_alias,
        rows=int(len(df_agg.index)),
        current_rows=int(len(frame.index)),
        selected_vars=selected_vars,
        source_hash=source_hash,
        var_counts=var_counts,
        parse_errors=parse_errors,
    )
    return frame, manifest, profile_feeders(frame)


def _manifest(
    *,
    source_alias: str,
    rows: int,
    current_rows: int,
    selected_vars: set[str],
    source_hash: str = "",
    var_counts: dict[str, int] | None = None,
    parse_errors: int = 0,
) -> dict[str, object]:
    return {
        "source_alias": source_alias,
        "source_hash": source_hash or stable_hash((source_alias, rows, current_rows), length=32),
        "source_kind": "dashboard_agg_dataframe",
        "total_rows": rows,
        "current_rows": current_rows,
        "selected_current_variables": sorted(selected_vars),
        "var_counts": var_counts or {},
        "parse_errors": parse_errors,
        "read_only": True,
        "content_opened": "in_memory_dashboard_aggregate_for_selected_current_variables_only",
    }
