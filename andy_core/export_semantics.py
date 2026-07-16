from __future__ import annotations

from typing import List, Optional, Tuple

import pandas as pd

from andy_core.capabilities import XlsxDashboardEngine
from measurement_value import normalize_measurement_series


def normalize_long_for_xlsx_agg(df_long: pd.DataFrame, *, round_values: bool = False) -> pd.DataFrame:
    req = ["timestamp", "equip_id", "var", "classe", "valor"]
    missing = [c for c in req if c not in df_long.columns]
    if missing:
        raise ValueError(f"Colunas ausentes no LONG: {missing}")

    extra_cols = [c for c in ["SE", "BAY", "TERMINAL"] if c in df_long.columns]
    df = df_long[req + extra_cols].copy()
    if "EQUIPAMENTO" in df_long.columns:
        equip = df_long["EQUIPAMENTO"].astype(str).str.strip()
        if equip.ne("").any():
            df["equip_id"] = equip
    elif "ponto_id" in df_long.columns:
        ponto = df_long["ponto_id"].astype(str).str.strip()
        if ponto.ne("").any():
            df["equip_id"] = ponto
    ts = pd.to_datetime(df["timestamp"], errors="coerce")
    if getattr(ts.dt, "tz", None) is not None:
        ts = ts.dt.tz_convert(None)
    df["timestamp"] = ts.dt.floor("s")
    df["equip_id"] = df["equip_id"].astype(str)
    df["var"] = df["var"].astype(str)
    df["classe"] = df["classe"].fillna("").astype(str)
    if "SE" not in df.columns:
        df["SE"] = ""
    if "BAY" not in df.columns:
        df["BAY"] = ""
    if "TERMINAL" not in df.columns:
        df["TERMINAL"] = ""
    df["SE"] = df["SE"].fillna("").astype(str)
    df["BAY"] = df["BAY"].fillna("").astype(str)
    df["TERMINAL"] = df["TERMINAL"].fillna("").astype(str)
    if round_values:
        df["valor"] = normalize_measurement_series(df["valor"], ndigits=1)
    return df.dropna(subset=["timestamp", "equip_id", "var", "valor"])


def normalize_agg_schema(df_agg: pd.DataFrame, *, round_values: bool = False) -> pd.DataFrame:
    expected = ["_TS", "_KEY", "_VAL", "_SE", "_BAY", "_TERMINAL", "_EQUIP", "_VAR", "_CLASSE"]

    if set(expected).issubset(df_agg.columns):
        out = df_agg.copy()
    elif {"timestamp", "equip_id", "var", "classe", "valor"}.issubset(df_agg.columns):
        out = df_agg.rename(
            columns={
                "timestamp": "_TS",
                "SE": "_SE",
                "BAY": "_BAY",
                "TERMINAL": "_TERMINAL",
                "equip_id": "_EQUIP",
                "var": "_VAR",
                "classe": "_CLASSE",
                "valor": "_VAL",
            }
        ).copy()
        out["_SE"] = out.get("_SE", "").astype(str)
        out["_BAY"] = out.get("_BAY", "").astype(str)
        out["_TERMINAL"] = out.get("_TERMINAL", "").astype(str)
        out["_KEY"] = (
            out["_SE"].fillna("").astype(str)
            + "|"
            + out["_BAY"].fillna("").astype(str)
            + "|"
            + out["_EQUIP"].astype(str)
            + "|"
            + out["_TERMINAL"].fillna("").astype(str)
            + "|"
            + out["_VAR"].astype(str)
        )
    else:
        raise ValueError(f"Schema de df_agg inesperado. Colunas: {list(df_agg.columns)}")

    out["_TS"] = pd.to_datetime(out["_TS"], errors="coerce")
    if round_values:
        out["_VAL"] = normalize_measurement_series(out["_VAL"], ndigits=1)
    out["_SE"] = out.get("_SE", "").fillna("").astype(str)
    out["_BAY"] = out.get("_BAY", "").fillna("").astype(str)
    out["_TERMINAL"] = out.get("_TERMINAL", "").fillna("").astype(str)
    out["_EQUIP"] = out["_EQUIP"].astype(str)
    out["_VAR"] = out["_VAR"].astype(str)
    out["_CLASSE"] = out["_CLASSE"].fillna("").astype(str)
    out["_KEY"] = out["_KEY"].astype(str)
    out = out.dropna(subset=["_TS", "_VAL", "_EQUIP", "_VAR"])
    return out[expected]


def call_xlsx_dashboard_engine(
    *,
    engine: XlsxDashboardEngine,
    df_agg: pd.DataFrame,
    out_path: str,
    equip_slots: int,
    var_slots: int,
    max_timestamps: int,
    report_meta: dict,
    selected_pairs: Optional[List[Tuple[str, str]]] = None,
    split_timestamp_columns: bool = False,
) -> Tuple[str, List[str]]:
    try:
        result = engine.build_workbook(
            long_df=df_agg,
            xlsx_out=out_path,
            report_meta=report_meta,
            equip_slots=int(equip_slots),
            var_slots=int(var_slots),
            max_timestamps=int(max_timestamps),
            selected_pairs=selected_pairs,
            split_timestamp_columns=bool(split_timestamp_columns),
        )
    except TypeError:
        result = engine.build_workbook(
            long_df=df_agg,
            xlsx_out=out_path,
            equip_slots=int(equip_slots),
            var_slots=int(var_slots),
            max_timestamps=int(max_timestamps),
        )
    if isinstance(result, tuple) and len(result) == 2:
        return str(result[0]), list(result[1] or [])
    return str(result), []
