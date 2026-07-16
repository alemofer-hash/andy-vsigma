from __future__ import annotations

import datetime as dt
import json
import logging
import math
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import pandas as pd
import streamlit as st
from audit.export_auditor import (
    ExportIntent,
    apply_recommendation,
    estimate_export_shape,
    run_audit,
)
from config import (
    AppConfig,
    PERFORMANCE_WARN_ROWS,
    XLSX_MAX_TIMESTAMPS_DEFAULT,
    detect_db_paths_in_lake,
    ensure_db_exists,
    resolve_db_path,
    get_source_root,
    load_config,
    safe_join_root,
)
from db.query_builder import (
    build_distinct_query,
    build_filters,
    build_order_by,
    build_pagination,
    build_ponto_query,
    build_vars_for_context_query,
    build_vars_for_pontos_query,
)
from measurement_value import normalize_measurement_series
from security.audit import audit_export, audit_export_risk, read_recent_audit_events
from security.auth import UserContext, get_user_context
from security.errors import handle_user_error, log_exception
from xlsx_selection import (
    expand_pairs,
    normalize_selections,
    pontos_to_xlsx_selection,
    validate_selections,
)

# Motor XLSX (reaproveita o gerador do report runner)
# Deixe andys_report_runner.py na MESMA pasta do app.
try:
    from andys_report_runner import aggregate_long, construir_bi_excel_multi_equip_multi_var_long
    BI_IMPORT_ERROR = None
except Exception as e:
    aggregate_long = None
    construir_bi_excel_multi_equip_multi_var_long = None
    BI_IMPORT_ERROR = e

ORDER_ALLOWLIST = {
    "timestamp": "timestamp",
    "equip_id": "equip_id, timestamp",
    "var": "var, timestamp",
    "SE": "SE, timestamp",
    "BAY": "BAY, timestamp",
    "EQUIPAMENTO": "EQUIPAMENTO, timestamp",
    "TERMINAL": "TERMINAL, timestamp",
    "ponto_id": "ponto_id, timestamp",
}
ORDER_OPTIONS = {
    "timestamp ASC": ("timestamp", "ASC"),
    "timestamp DESC": ("timestamp", "DESC"),
    "equip_id ASC, timestamp ASC": ("equip_id", "ASC"),
    "var ASC, timestamp ASC": ("var", "ASC"),
    "SE ASC, timestamp ASC": ("SE", "ASC"),
    "BAY ASC, timestamp ASC": ("BAY", "ASC"),
    "TERMINAL ASC, timestamp ASC": ("TERMINAL", "ASC"),
}

st.set_page_config(page_title="Andy's Lake Viewer", layout="wide")


# --- CHANGED: guard de conexao retorna None em falha para diagnostico amigavel ---
@st.cache_resource
def get_con(db_path: str):
    try:
        con = duckdb.connect(db_path, read_only=True)
        con.execute("PRAGMA threads=4;")
        con.execute("SELECT 1 FROM medicoes LIMIT 1;").fetchone()
        return con
    except Exception:
        return None


# --- NEW: exige conexao valida e mostra status visivel no sidebar ---
def require_connection(db_path: str):
    con = get_con(db_path)
    if con is None:
        st.sidebar.error("DB: offline")
        st.error(
            "Could not connect to DuckDB or query `medicoes`. "
            "Check ANDYS_DB_PATH and ensure the indexer has already created the database."
        )
        st.stop()
    st.sidebar.success("DB: online")
    return con


# --- NEW: usa cursor isolado por operacao para evitar estado compartilhado instavel ---
def get_cur(db_path: str):
    con = get_con(db_path)
    if con is None:
        raise RuntimeError("DuckDB connection is unavailable.")
    return con.cursor()


@st.cache_data(ttl=60)
def load_overview(db_path: str):
    cur = get_cur(db_path)

    overview = cur.execute(
        """
        SELECT
          COUNT(*) AS rows_total,
          MIN(timestamp) AS ts_min,
          MAX(timestamp) AS ts_max,
          COUNT(DISTINCT equip_id) AS equips_distintos,
          COUNT(DISTINCT var) AS vars_distintas
        FROM medicoes;
        """
    ).df()

    by_month = cur.execute(
        """
        SELECT ano, mes, COUNT(*) AS rows
        FROM medicoes
        GROUP BY ano, mes
        ORDER BY ano, mes;
        """
    ).df()

    vars_ = cur.execute(
        """
        SELECT var, classe, COUNT(*) AS rows
        FROM medicoes
        GROUP BY var, classe
        ORDER BY rows DESC;
        """
    ).df()

    top_equips = cur.execute(
        """
        SELECT equip_id, COUNT(*) AS rows, MIN(timestamp) AS ts_min, MAX(timestamp) AS ts_max
        FROM medicoes
        GROUP BY equip_id
        ORDER BY rows DESC
        LIMIT 50;
        """
    ).df()

    return overview, by_month, vars_, top_equips


@st.cache_data(ttl=60)
def get_medicoes_columns(db_path: str) -> List[Tuple[str, str]]:
    cur = get_cur(db_path)
    rows = cur.execute("DESCRIBE SELECT * FROM medicoes;").fetchall()
    return [(str(r[0]), str(r[1])) for r in rows]


def _column_set(db_path: str) -> set[str]:
    return {c for c, _ in get_medicoes_columns(db_path)}


def _quote_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _is_safe_filter_col(name: str) -> bool:
    return str(name).replace("_", "").isalnum()


def _projected_base_select(db_path: str) -> str:
    cols = _column_set(db_path)

    def pick(col: str, fallback: Optional[str] = None, cast: str = "VARCHAR") -> str:
        if col in cols:
            return f"CAST({col} AS {cast}) AS {col}" if cast else col
        if fallback and fallback in cols:
            return f"CAST({fallback} AS {cast}) AS {col}" if cast else f"{fallback} AS {col}"
        return f"CAST(NULL AS {cast}) AS {col}"

    valor_expr = (
        "COALESCE("
        "TRY_CAST(valor AS DOUBLE), "
        "TRY_CAST(REPLACE(CAST(valor AS VARCHAR), ',', '.') AS DOUBLE), "
        "TRY_CAST(REPLACE(REPLACE(CAST(valor AS VARCHAR), '.', ''), ',', '.') AS DOUBLE)"
        ")"
    )

    ts_expr = "CAST(NULL AS TIMESTAMP)"
    has_ts = "timestamp" in cols
    has_ts_raw = "TIMESTAMP" in cols
    if has_ts and has_ts_raw:
        ts_expr = (
            "COALESCE("
            "TRY_CAST(timestamp AS TIMESTAMP), "
            "TRY_STRPTIME(CAST(TIMESTAMP AS VARCHAR), '%d/%m/%Y %H:%M:%S'), "
            "TRY_STRPTIME(CAST(TIMESTAMP AS VARCHAR), '%d/%m/%Y %H:%M'), "
            "TRY_STRPTIME(CAST(TIMESTAMP AS VARCHAR), '%d/%m/%Y'), "
            "TRY_CAST(TIMESTAMP AS TIMESTAMP)"
            ")"
        )
    elif has_ts:
        ts_expr = "TRY_CAST(timestamp AS TIMESTAMP)"
    elif has_ts_raw:
        ts_expr = (
            "COALESCE("
            "TRY_STRPTIME(CAST(TIMESTAMP AS VARCHAR), '%d/%m/%Y %H:%M:%S'), "
            "TRY_STRPTIME(CAST(TIMESTAMP AS VARCHAR), '%d/%m/%Y %H:%M'), "
            "TRY_STRPTIME(CAST(TIMESTAMP AS VARCHAR), '%d/%m/%Y'), "
            "TRY_CAST(TIMESTAMP AS TIMESTAMP)"
            ")"
        )

    select_items = [
        f"{ts_expr} AS timestamp",
        pick("SE"),
        pick("BAY"),
        pick("EQUIPAMENTO", fallback="equip_id"),
        pick("TERMINAL"),
        pick("ponto_id"),
        pick("equip_id", fallback="EQUIPAMENTO"),
        pick("var"),
        pick("classe"),
        f"{valor_expr} AS valor" if "valor" in cols else "CAST(NULL AS DOUBLE) AS valor",
        pick("ano", cast="INTEGER"),
        pick("mes", cast="INTEGER"),
    ]
    return ", ".join(select_items)


@st.cache_data(ttl=30)
def get_distinct_values(db_path: str, col: str, limit: int = 500) -> List[str]:
    cur = get_cur(db_path)
    col_q = _quote_ident(col)
    q = f"SELECT DISTINCT CAST({col_q} AS VARCHAR) AS v FROM medicoes WHERE {col_q} IS NOT NULL ORDER BY 1 LIMIT {int(limit)};"
    return [str(r[0]) for r in cur.execute(q).fetchall() if str(r[0]).strip()]


@st.cache_data(ttl=30)
def get_numeric_range(db_path: str, col: str) -> Tuple[Optional[float], Optional[float]]:
    cur = get_cur(db_path)
    col_q = _quote_ident(col)
    q = (
        "SELECT "
        f"MIN(COALESCE(TRY_CAST({col_q} AS DOUBLE), TRY_CAST(REPLACE(CAST({col_q} AS VARCHAR), ',', '.') AS DOUBLE), "
        f"TRY_CAST(REPLACE(REPLACE(CAST({col_q} AS VARCHAR), '.', ''), ',', '.') AS DOUBLE))), "
        f"MAX(COALESCE(TRY_CAST({col_q} AS DOUBLE), TRY_CAST(REPLACE(CAST({col_q} AS VARCHAR), ',', '.') AS DOUBLE), "
        f"TRY_CAST(REPLACE(REPLACE(CAST({col_q} AS VARCHAR), '.', ''), ',', '.') AS DOUBLE))) "
        "FROM medicoes "
        f"WHERE COALESCE(TRY_CAST({col_q} AS DOUBLE), TRY_CAST(REPLACE(CAST({col_q} AS VARCHAR), ',', '.') AS DOUBLE), "
        f"TRY_CAST(REPLACE(REPLACE(CAST({col_q} AS VARCHAR), '.', ''), ',', '.') AS DOUBLE)) IS NOT NULL;"
    )
    try:
        row = cur.execute(q).fetchone()
    except Exception:
        logging.warning("Falha ao calcular range numerico para coluna '%s'. Ignorando filtro de range.", col)
        return None, None
    if row is None:
        return None, None
    lo = float(row[0]) if row[0] is not None else None
    hi = float(row[1]) if row[1] is not None else None
    return lo, hi


@st.cache_data(ttl=20)
def load_ingestion_metadata(lake_root: str) -> Tuple[Dict[str, Any], pd.DataFrame]:
    cfg_path = os.path.join(lake_root, "andys_config.json")
    manifest_path = os.path.join(lake_root, "manifest.json")

    cfg: Dict[str, Any] = {}
    files_df = pd.DataFrame(columns=["file", "indexed_at", "source_size", "source_mtime", "rows_long"])

    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        rows: List[Dict[str, Any]] = []
        for k, v in (manifest.get("files") or {}).items():
            rows.append(
                {
                    "file": k,
                    "indexed_at": v.get("indexed_at"),
                    "source_size": v.get("source_size"),
                    "source_mtime": v.get("source_mtime"),
                    "rows_long": v.get("rows_long"),
                }
            )
        files_df = pd.DataFrame(rows).sort_values("indexed_at", ascending=False) if rows else files_df

    return cfg, files_df


@st.cache_data(ttl=10)
def query_page(
    db_path: str,
    where_sql: str,
    where_params: Tuple[object, ...],
    pagination_sql: str,
    pagination_params: Tuple[int, int],
    order_sql: str,
):
    cur = get_cur(db_path)
    select_projection = _projected_base_select(db_path)
    count_row = cur.execute(
        f"SELECT COUNT(*) AS n FROM medicoes WHERE {where_sql};",
        where_params,
    ).fetchone()
    if count_row is None:
        raise RuntimeError(f"COUNT(*) retornou vazio para where_sql={where_sql!r}")
    total = int(count_row[0] or 0)
    df = cur.execute(
        f"""
        WITH base AS (
          SELECT {select_projection}
          FROM medicoes
          WHERE {where_sql}
        )
        SELECT * FROM base
        {order_sql}
        {pagination_sql};
        """,
        where_params + pagination_params,
    ).df()
    if "valor" in df.columns:
        df["valor"] = normalize_measurement_series(df["valor"], ndigits=1)
    return total, df


def query_full_long(
    db_path: str,
    where_sql: str,
    where_params: Tuple[object, ...],
    limit_cap: Optional[int] = None,
) -> pd.DataFrame:
    """
    Puxa o recorte COMPLETO em LONG (com base nos filtros).
    Usa LIMIT opcional como cinto de seguranca.
    """
    cur = get_cur(db_path)
    select_projection = _projected_base_select(db_path)
    sql = f"""
    WITH base AS (
      SELECT {select_projection}
      FROM medicoes
      WHERE {where_sql}
    )
    SELECT * FROM base
    ORDER BY timestamp ASC
    """
    params: Tuple[object, ...] = where_params
    if limit_cap:
        sql += " LIMIT ?"
        params = where_params + (int(limit_cap),)
    sql += ";"
    df = cur.execute(sql, params).df()
    if "valor" in df.columns:
        df["valor"] = normalize_measurement_series(df["valor"], ndigits=1)
    return df


@st.cache_data(ttl=30)
def load_vars_by_equip(
    db_path: str,
    equips: Tuple[str, ...],
    ano: Optional[int],
    mes: Optional[int],
    t0: Optional[str],
    t1: Optional[str],
) -> Dict[str, List[str]]:
    cur = get_cur(db_path)
    cols = _column_set(db_path)
    equip_col = "EQUIPAMENTO" if "EQUIPAMENTO" in cols else "equip_id"
    out: Dict[str, List[str]] = {}
    for equip in equips:
        clauses = [f"{equip_col} = ?"]
        params: List[object] = [equip]
        if ano is not None:
            clauses.append("ano = ?")
            params.append(int(ano))
        if mes is not None:
            clauses.append("mes = ?")
            params.append(int(mes))
        if t0:
            clauses.append("timestamp >= CAST(? AS TIMESTAMP)")
            params.append(str(t0))
        if t1:
            clauses.append("timestamp <= CAST(? AS TIMESTAMP)")
            params.append(str(t1))
        q = f"SELECT DISTINCT var FROM medicoes WHERE {' AND '.join(clauses)} ORDER BY var;"
        vars_eq = [str(r[0]) for r in cur.execute(q, params).fetchall()]
        out[equip] = vars_eq
    return out


@st.cache_data(ttl=30)
def load_distinct_options(
    db_path: str,
    *,
    target_col: str,
    ano: Optional[int],
    mes: Optional[int],
    t0: Optional[str],
    t1: Optional[str],
    se_sel: Tuple[str, ...] = (),
    bay_sel: Tuple[str, ...] = (),
    equipamento_sel: Tuple[str, ...] = (),
    terminal_sel: Tuple[str, ...] = (),
    ponto_id_like: str = "",
    limit: int = 500,
) -> List[str]:
    cur = get_cur(db_path)
    sql, params = build_distinct_query(
        target_col=target_col,
        ano=ano,
        mes=mes,
        t0=t0,
        t1=t1,
        se_sel=list(se_sel),
        bay_sel=list(bay_sel),
        equipamento_sel=list(equipamento_sel),
        terminal_sel=list(terminal_sel),
        ponto_id_like=ponto_id_like,
        limit=limit,
        include_empty=(target_col == "BAY"),
    )
    out: List[str] = []
    for row in cur.execute(sql, params).fetchall():
        val = row[0]
        if val is None:
            continue
        sval = str(val)
        if target_col != "BAY" and not sval.strip():
            continue
        out.append(sval)
    return out


@st.cache_data(ttl=30)
def load_ponto_options(
    db_path: str,
    *,
    ano: Optional[int],
    mes: Optional[int],
    t0: Optional[str] = None,
    t1: Optional[str] = None,
    se_sel: Tuple[str, ...] = (),
    bay_sel: Tuple[str, ...] = (),
    equipamento_sel: Tuple[str, ...] = (),
    terminal_sel: Tuple[str, ...] = (),
    ponto_id_like: str = "",
    limit: int = 500,
) -> List[str]:
    cur = get_cur(db_path)
    sql, params = build_ponto_query(
        ano=ano,
        mes=mes,
        se_sel=list(se_sel),
        bay_sel=list(bay_sel),
        equipamento_sel=list(equipamento_sel),
        terminal_sel=list(terminal_sel),
        ponto_id_like=ponto_id_like,
        limit=limit,
    )
    return [str(r[0]) for r in cur.execute(sql, params).fetchall() if r[0] is not None]


@st.cache_data(ttl=30)
def load_vars_by_pontos(
    db_path: str,
    pontos: Tuple[str, ...],
    *,
    ano: Optional[int],
    mes: Optional[int],
    t0: Optional[str] = None,
    t1: Optional[str] = None,
) -> List[str]:
    if not pontos:
        return []
    # --- CHANGED: deduplica ponto_id para evitar inflacao por repeticoes acidentais ---
    pontos_unique = tuple(dict.fromkeys(str(p).strip() for p in pontos if str(p).strip()))
    if not pontos_unique:
        return []
    cur = get_cur(db_path)
    sql, params = build_vars_for_pontos_query(
        ano=ano,
        mes=mes,
        ponto_ids_sel=list(pontos_unique),
    )
    return [str(r[0]) for r in cur.execute(sql, params).fetchall() if str(r[0]).strip()]


# --- NEW: descoberta de variaveis por contexto sem enumerar todos os ponto_ids ---
@st.cache_data(ttl=30)
def load_vars_by_context(
    db_path: str,
    *,
    ano: Optional[int],
    mes: Optional[int],
    se_sel: Tuple[str, ...] = (),
    bay_sel: Tuple[str, ...] = (),
    equipamento_sel: Tuple[str, ...] = (),
    terminal_sel: Tuple[str, ...] = (),
    ponto_id_like: str = "",
) -> List[str]:
    cur = get_cur(db_path)
    sql, params = build_vars_for_context_query(
        ano=ano,
        mes=mes,
        se_sel=list(se_sel),
        bay_sel=list(bay_sel),
        equipamento_sel=list(equipamento_sel),
        terminal_sel=list(terminal_sel),
        ponto_id_like=ponto_id_like,
    )
    return [str(r[0]) for r in cur.execute(sql, params).fetchall() if str(r[0]).strip()]


def _prune_state(key: str, valid_options: List[str]) -> None:
    current = st.session_state.get(key, [])
    if not isinstance(current, list):
        st.session_state[key] = []
        return
    valid = set(valid_options)
    st.session_state[key] = [x for x in current if x in valid]


# --- NEW: auto-preenchimento de filtro quando resta apenas uma opcao valida ---
def _autofill_single_option(key: str, valid_options: List[str]) -> bool:
    current = st.session_state.get(key, [])
    if not isinstance(current, list):
        current = []
    if len(valid_options) != 1:
        return False
    only = valid_options[0]
    current_valid = [v for v in current if v in set(valid_options)]
    if current_valid == [only]:
        return False
    if current_valid and current_valid != [only]:
        st.session_state[key] = [only]
        return True
    if not current_valid:
        st.session_state[key] = [only]
        return True
    return False


# --- NEW: simplifica workflow de ponto usando todos os candidatos quando nao ha selecao manual ---
def _resolve_effective_points(ponto_options: List[str]) -> List[str]:
    # --- CHANGED: deduplicacao estavel para garantir conjunto real de pontos ---
    return list(dict.fromkeys(str(p).strip() for p in ponto_options if str(p).strip()))


def _resolve_points_backend(
    db_path: str,
    *,
    ano: Optional[int],
    mes: Optional[int],
    se_sel: Tuple[str, ...],
    bay_sel: Tuple[str, ...],
    equipamento_sel: Tuple[str, ...],
    terminal_sel: Tuple[str, ...],
    ponto_id_like: str,
    limit: int,
) -> List[str]:
    return load_ponto_options(
        db_path,
        ano=ano,
        mes=mes,
        t0=None,
        t1=None,
        se_sel=se_sel,
        bay_sel=bay_sel,
        equipamento_sel=equipamento_sel,
        terminal_sel=terminal_sel,
        ponto_id_like=ponto_id_like,
        limit=limit,
    )


def _format_option_label(value: str) -> str:
    return str(value) if str(value).strip() else "(vazio)"


def _equip_ids_from_pontos(selected_pontos: List[str]) -> List[str]:
    equips: set[str] = set()
    for ponto in selected_pontos or []:
        parts = str(ponto).split("|")
        if len(parts) < 3:
            continue
        equip = str(parts[2]).strip()
        if equip:
            equips.add(equip)
    return sorted(equips)


def _month_bounds(ano: int, mes: int) -> Tuple[str, str]:
    start = dt.datetime(int(ano), int(mes), 1, 0, 0, 0)
    if int(mes) == 12:
        next_month = dt.datetime(int(ano) + 1, 1, 1, 0, 0, 0)
    else:
        next_month = dt.datetime(int(ano), int(mes) + 1, 1, 0, 0, 0)
    end = next_month - dt.timedelta(seconds=1)
    return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")


def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


def _new_correlation_id() -> str:
    return uuid.uuid4().hex[:12]


def _show_error(exc: Exception, cfg: AppConfig, cid: str, context: Dict[str, Any]) -> None:
    log_exception(exc, cid, context)
    st.error(handle_user_error(exc, cid, cfg.is_prod))


def _app_headers() -> Dict[str, str]:
    try:
        headers = getattr(st.context, "headers", None)  # type: ignore[attr-defined]
        return dict(headers) if headers else {}
    except Exception:
        return {}


def _sanitize_audit_filters(
    *,
    t0: str,
    t1: str,
    equips_selected: List[str],
    vars_sel: List[str],
    agg: str,
    time_floor: str,
    max_timestamps: int,
) -> Dict[str, Any]:
    return {
        "t0": t0[:19],
        "t1": t1[:19],
        "n_equips": len(equips_selected),
        "n_vars": len(vars_sel),
        "agg": agg,
        "time_floor": time_floor[:16],
        "max_timestamps": int(max_timestamps),
    }


def _serialize_findings(findings: List[Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for f in findings:
        out.append(
            {
                "code": str(getattr(f, "code", "")),
                "severity": str(getattr(f, "severity", "")),
                "title": str(getattr(f, "title", "")),
                "hard_stop": bool(getattr(f, "hard_stop", False)),
            }
        )
    return out


def _risk_status(findings: List[Any]) -> str:
    if any(str(getattr(f, "severity", "")) == "ERROR" for f in findings):
        return "ERROR"
    if any(str(getattr(f, "severity", "")) == "WARN" for f in findings):
        return "WARN"
    return "OK"


def _db_bootstrap_diagnostics(cfg: AppConfig, db_path: str) -> Dict[str, Any]:
    p = os.path.abspath(db_path)
    return {
        "env": cfg.env,
        "db_path": p,
        "db_exists": os.path.exists(p),
        "lake_root": cfg.lake_root,
        "lake_exists": os.path.isdir(cfg.lake_root),
        "allowed_root": cfg.allowed_root or "",
    }


def resolve_db_for_app(
    cfg: AppConfig,
    *,
    db_path_input: Optional[str] = None,
    auto_detect: bool = True,
) -> Tuple[str, Dict[str, Any]]:
    resolved = resolve_db_path(
        work_root=cfg.work_root,
        lake_root=cfg.lake_root,
        db_path_override=db_path_input or cfg.db_path,
        allowed_root=cfg.allowed_root,
        source_root=cfg.source_root,
    )
    diag = _db_bootstrap_diagnostics(cfg, resolved)

    if not diag["db_exists"] and auto_detect:
        hits = detect_db_paths_in_lake(cfg.lake_root, allowed_root=cfg.allowed_root)
        diag["autodetect_candidates"] = hits
        if len(hits) == 1:
            resolved = hits[0]
            diag["autodetect_used"] = True
            diag["db_path"] = resolved
            diag["db_exists"] = True
        else:
            diag["autodetect_used"] = False
    else:
        diag["autodetect_candidates"] = []
        diag["autodetect_used"] = False

    ensure_db_exists(resolved, lake_root=cfg.lake_root)
    return resolved, diag


def _normalize_for_agg(df_long: pd.DataFrame) -> pd.DataFrame:
    req = ["timestamp", "equip_id", "var", "classe", "valor"]
    missing = [c for c in req if c not in df_long.columns]
    if missing:
        raise ValueError(f"Colunas ausentes no LONG: {missing}")

    extra_cols = [c for c in ["SE", "BAY", "TERMINAL"] if c in df_long.columns]
    df = df_long[req + extra_cols].copy()
    # A selecao XLSX no app e feita por EQUIPAMENTO; manter a mesma chave evita
    # recorte vazio por mismatch com _KEY após agregacao.
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
    ts = ts.dt.floor("s")
    df["timestamp"] = ts
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
    df["valor"] = normalize_measurement_series(df["valor"], ndigits=1)
    df = df.dropna(subset=["timestamp", "equip_id", "var", "valor"])
    return df


def _normalize_agg_schema(df_agg: pd.DataFrame) -> pd.DataFrame:
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


def _call_xlsx_engine(
    df_agg: pd.DataFrame,
    out_path: str,
    equip_slots: int,
    var_slots: int,
    max_timestamps: int,
    report_meta: dict,
    selected_pairs: Optional[List[Tuple[str, str]]] = None,
) -> Tuple[str, List[str]]:
    # Compatibilidade com assinaturas nova/antiga do report runner.
    try:
        result = construir_bi_excel_multi_equip_multi_var_long(
            long_df=df_agg,
            xlsx_out=out_path,
            report_meta=report_meta,
            equip_slots=equip_slots,
            var_slots=var_slots,
            max_timestamps=max_timestamps,
            selected_pairs=selected_pairs,
        )
    except TypeError:
        result = construir_bi_excel_multi_equip_multi_var_long(
            long_df=df_agg,
            xlsx_out=out_path,
            equip_slots=equip_slots,
            var_slots=var_slots,
            max_timestamps=max_timestamps,
        )

    if isinstance(result, tuple) and len(result) == 2:
        return str(result[0]), list(result[1] or [])
    return str(result), []


def main():
    cid = _new_correlation_id()
    cfg: Optional[AppConfig] = None
    try:
        cfg = load_config(source_root_override=st.session_state.get("source_root_override"))
        logging.basicConfig(level=getattr(logging, cfg.log_level, logging.INFO))
        headers = _app_headers()
        user_ctx: UserContext = get_user_context(cfg, headers)

        st.title("Andy's Lake - Tabela + Exportacao (CSV / XLSX Dashboard)")
        st.caption("Tabela paginada com filtros. Exporta recorte filtrado e relatorio XLSX.")

        if cfg.is_prod:
            db_input = cfg.db_path
            export_dir = cfg.export_dir
            source_root = cfg.source_root
            st.sidebar.caption("Modo producao: caminhos definidos por variaveis de ambiente.")
            st.sidebar.text_input("SOURCE_ROOT (somente leitura)", value=source_root, disabled=True)
            st.sidebar.text_input("DuckDB (somente leitura)", value=db_input, disabled=True)
        else:
            source_input = st.sidebar.text_input("SOURCE_ROOT (somente leitura)", cfg.source_root)
            source_root = get_source_root(source_input)
            st.session_state["source_root_override"] = source_root
            db_input = st.sidebar.text_input("Caminho do DuckDB", cfg.db_path)
            export_input = st.sidebar.text_input("Pasta de exportacao", cfg.export_dir)
            if cfg.allowed_root:
                export_dir = safe_join_root(cfg.allowed_root, export_input)
            else:
                export_dir = os.path.abspath(export_input)

            if st.sidebar.button("Validar DB"):
                try:
                    validated_db, _ = resolve_db_for_app(cfg, db_path_input=db_input, auto_detect=False)
                    con_check = duckdb.connect(validated_db, read_only=True)
                    try:
                        con_check.execute("SELECT 1;").fetchone()
                        tables = [str(r[0]) for r in con_check.execute("SHOW TABLES;").fetchall()]
                    finally:
                        con_check.close()
                    st.sidebar.success(f"DB valido: {validated_db}")
                    if "medicoes" not in {t.lower() for t in tables}:
                        st.sidebar.warning("DB abriu, mas a tabela/view 'medicoes' nao foi encontrada.")
                except Exception as exc:
                    st.sidebar.error(f"Falha ao validar DB: {exc}")
        st.caption(f"SOURCE_ROOT ativo (read-only): `{source_root}`")

        try:
            db_path, db_diag = resolve_db_for_app(cfg, db_path_input=db_input, auto_detect=True)
            if db_diag.get("autodetect_used"):
                st.info(f"DB detectado automaticamente no lake: `{db_path}`")
            con_health = duckdb.connect(db_path, read_only=True)
            try:
                con_health.execute("SELECT 1;").fetchone()
                tables = {str(r[0]).lower() for r in con_health.execute("SHOW TABLES;").fetchall()}
            finally:
                con_health.close()
            if "medicoes" not in tables:
                st.error("DuckDB encontrado, mas a tabela/view 'medicoes' nao existe.")
                st.caption("Rode novamente a indexacao para reconstruir o catalogo.")
                st.code(".\\.venv\\Scripts\\python.exe .\\andys_indexer.py", language="powershell")
                st.stop()
        except (FileNotFoundError, ValueError) as exc:
            try:
                fallback_path = resolve_db_path(
                    work_root=cfg.work_root,
                    lake_root=cfg.lake_root,
                    db_path_override=db_input,
                    allowed_root=cfg.allowed_root,
                    source_root=cfg.source_root,
                )
            except Exception:
                fallback_path = str(db_input)
            db_diag = _db_bootstrap_diagnostics(cfg, fallback_path)
            db_diag["autodetect_candidates"] = detect_db_paths_in_lake(cfg.lake_root, allowed_root=cfg.allowed_root)
            logging.error(
                "cid=%s db_bootstrap_failed env=%s db_path=%s exists=%s lake_root=%s allowed_root=%s error=%s",
                cid,
                cfg.env,
                db_diag.get("db_path"),
                db_diag.get("db_exists"),
                db_diag.get("lake_root"),
                db_diag.get("allowed_root"),
                str(exc),
            )
            st.error("Banco DuckDB nao encontrado para o app.")
            st.caption("Causas comuns: indexacao nao executada, caminho do DB invalido, root alterado ou bloqueio por allowlist.")
            with st.expander("Diagnostico"):
                st.json(db_diag)
            st.markdown("**Como corrigir**")
            st.code(".\\.venv\\Scripts\\python.exe .\\andys_indexer.py", language="powershell")
            st.caption(f"Verifique se o arquivo existe em: `{cfg.lake_root}\\andys.duckdb`")
            if cfg.is_prod:
                st.caption("Em producao, ajuste ANDYS_DB_PATH e ANDYS_ALLOWED_ROOT no ambiente.")
            else:
                st.caption("Em dev, ajuste o campo 'Caminho do DuckDB' na sidebar e clique em 'Validar DB'.")
                if os.path.isdir(cfg.lake_root) and st.button("Abrir pasta do lake"):
                    try:
                        os.startfile(cfg.lake_root)  # type: ignore[attr-defined]
                    except Exception as open_exc:
                        st.warning(f"Nao foi possivel abrir a pasta: {open_exc}")
            st.stop()

        require_connection(db_path)

        if BI_IMPORT_ERROR is not None and not cfg.is_prod:
            st.warning("Motor BI indisponivel no ambiente atual.")

        overview, by_month, vars_df, top_equips = load_overview(db_path)

        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("Resumo")
            st.dataframe(overview, width="stretch")
        with c2:
            st.subheader("Linhas por mes")
            st.dataframe(by_month, width="stretch", height=220)

        st.subheader("Variaveis disponiveis")
        st.dataframe(vars_df, width="stretch", height=220)

        with st.expander("Top equipamentos (por volume)"):
            st.dataframe(top_equips, width="stretch", height=300)

        with st.expander("Metadados de ingestao / origem"):
            ingest_cfg, ingest_files = load_ingestion_metadata(cfg.lake_root)
            source_from_cfg = ingest_cfg.get("source_root", cfg.source_root)
            st.write(f"Source root configurado no indexador: `{source_from_cfg}`")
            st.write(
                "Observacao: acesso ao share SMB ocorre no backend (indexador), "
                "nao aparece na aba Network do navegador."
            )
            if not ingest_files.empty:
                st.dataframe(ingest_files.head(50), width="stretch", height=260)
            else:
                st.info("Manifest de indexacao ainda nao encontrado em ANDYS_LAKE.")

        if user_ctx.is_admin and (not cfg.is_prod or cfg.admin_diag_enabled):
            st.info(f"Contexto: user={user_ctx.user_id} role={user_ctx.role} source={user_ctx.source}")

        st.divider()
        st.subheader("Tabela (paginada) + Filtros")

        anos = sorted(by_month["ano"].unique().tolist()) if not by_month.empty else []
        meses = sorted(by_month["mes"].unique().tolist()) if not by_month.empty else list(range(1, 13))
        all_cols = get_medicoes_columns(db_path)
        col_names = [c[0] for c in all_cols]
        for key, default in {
            "filter_se": [],
            "filter_bay": [],
            "filter_equip": [],
            "filter_terminal": [],
            "filter_vars": [],
            "ponto_id_search": "",
        }.items():
            if key not in st.session_state:
                st.session_state[key] = default

        if not anos:
            st.error("Sem anos disponiveis em `medicoes`.")
            st.stop()
        ano_default = max(anos)
        meses_ano_default = sorted(by_month[by_month["ano"] == ano_default]["mes"].unique().tolist()) if not by_month.empty else meses
        meses_para_select = meses_ano_default or meses
        mes_default = max(meses_para_select) if meses_para_select else max(meses)

        st.sidebar.markdown("### Filtros de contexto")
        ano = st.sidebar.selectbox("Ano", options=anos, index=anos.index(ano_default), key="filter_ano")
        meses_ano = sorted(by_month[by_month["ano"] == ano]["mes"].unique().tolist()) if not by_month.empty else meses
        meses_ano = meses_ano or meses
        mes = st.sidebar.selectbox("Mes", options=meses_ano, index=meses_ano.index(mes_default) if mes_default in meses_ano else len(meses_ano) - 1, key="filter_mes")
        period_t0, period_t1 = _month_bounds(int(ano), int(mes))

        t0 = None
        t1 = None
        ponto_id_search = st.sidebar.text_input(
            "Buscar ponto (SE|BAY|EQUIPAMENTO|TERMINAL)",
            value=st.session_state.get("ponto_id_search", ""),
            key="ponto_id_search",
        ).strip()

        se_options = (
            load_distinct_options(
                db_path,
                target_col="SE",
                ano=ano,
                mes=mes,
                t0=None,
                t1=None,
                ponto_id_like=ponto_id_search,
            )
            if "SE" in col_names
            else []
        )
        _prune_state("filter_se", se_options)

        se_sel = st.sidebar.multiselect("SE", options=se_options, key="filter_se")

        bay_options = (
            load_distinct_options(
                db_path,
                target_col="BAY",
                ano=ano,
                mes=mes,
                t0=None,
                t1=None,
                se_sel=tuple(se_sel),
                ponto_id_like=ponto_id_search,
            )
            if "BAY" in col_names
            else []
        )
        _prune_state("filter_bay", bay_options)
        _autofill_single_option("filter_bay", bay_options)
        bay_sel = st.sidebar.multiselect("BAY", options=bay_options, key="filter_bay", format_func=_format_option_label)

        equip_options = (
            load_distinct_options(
                db_path,
                target_col="EQUIPAMENTO",
                ano=ano,
                mes=mes,
                t0=None,
                t1=None,
                se_sel=tuple(se_sel),
                bay_sel=tuple(bay_sel),
                ponto_id_like=ponto_id_search,
            )
            if "EQUIPAMENTO" in col_names
            else []
        )
        _prune_state("filter_equip", equip_options)
        _autofill_single_option("filter_equip", equip_options)
        equips_selected = st.sidebar.multiselect("EQUIPAMENTO", options=equip_options, key="filter_equip")

        terminal_options = (
            load_distinct_options(
                db_path,
                target_col="TERMINAL",
                ano=ano,
                mes=mes,
                t0=None,
                t1=None,
                se_sel=tuple(se_sel),
                bay_sel=tuple(bay_sel),
                equipamento_sel=tuple(equips_selected),
                ponto_id_like=ponto_id_search,
            )
            if "TERMINAL" in col_names
            else []
        )
        _prune_state("filter_terminal", terminal_options)
        _autofill_single_option("filter_terminal", terminal_options)
        terminal_sel = st.sidebar.multiselect(
            "TERMINAL",
            options=terminal_options,
            key="filter_terminal",
            format_func=_format_option_label,
        )

        ponto_limit = 500
        ponto_options = _resolve_points_backend(
            db_path,
            ano=ano,
            mes=mes,
            se_sel=tuple(se_sel),
            bay_sel=tuple(bay_sel),
            equipamento_sel=tuple(equips_selected),
            terminal_sel=tuple(terminal_sel),
            ponto_id_like=ponto_id_search,
            limit=ponto_limit,
        )
        if len(ponto_options) >= ponto_limit:
            st.sidebar.caption("Limite de 500 pontos exibidos. Refine os filtros.")
        effective_selected_pontos = _resolve_effective_points(ponto_options)
        st.session_state["selected_pontos_resolved"] = effective_selected_pontos
        st.sidebar.caption(f"Resolved points: {len(effective_selected_pontos)}")

        vars_options = load_vars_by_context(
            db_path,
            ano=ano,
            mes=mes,
            se_sel=tuple(se_sel),
            bay_sel=tuple(bay_sel),
            equipamento_sel=tuple(equips_selected),
            terminal_sel=tuple(terminal_sel),
            ponto_id_like=ponto_id_search,
        )
        _prune_state("filter_vars", vars_options)
        vars_sel = st.sidebar.multiselect(
            "Variaveis (escopo dos pontos)",
            options=vars_options,
            key="filter_vars",
            disabled=not effective_selected_pontos,
        )

        colp1, colp2 = st.columns([1, 1])
        with colp1:
            page_size = st.selectbox("Linhas por pagina", [200, 500, 1000, 2000, 5000], index=2)
        with colp2:
            order_label = st.selectbox("Ordenar por", list(ORDER_OPTIONS.keys()), index=0)

        if not effective_selected_pontos:
            st.info("Refine os filtros para obter ao menos 1 ponto e carregar variaveis.")

        sort_key, sort_dir = ORDER_OPTIONS[order_label]
        order_sql = build_order_by(sort_key, sort_dir, ORDER_ALLOWLIST)

        advanced_equals: Dict[str, List[str]] = {}
        advanced_ranges: Dict[str, Tuple[float, float]] = {}
        with st.expander("Filtros Avancados (todas as colunas)"):
            key_skip = {
                "timestamp", "SE", "BAY", "EQUIPAMENTO", "TERMINAL", "equip_id",
                "var", "valor", "ano", "mes", "ponto_id"
            }
            for col_name, col_type in all_cols:
                if col_name in key_skip:
                    continue
                if not _is_safe_filter_col(col_name):
                    continue
                type_up = col_type.upper()
                if any(t in type_up for t in ["DOUBLE", "DECIMAL", "FLOAT", "BIGINT", "INTEGER"]):
                    lo, hi = get_numeric_range(db_path, col_name)
                    if lo is not None and hi is not None and lo < hi:
                        rng = st.slider(f"{col_name} (range)", min_value=float(lo), max_value=float(hi), value=(float(lo), float(hi)))
                        if rng[0] > lo or rng[1] < hi:
                            advanced_ranges[col_name] = (float(rng[0]), float(rng[1]))
                else:
                    vals = get_distinct_values(db_path, col_name, limit=80)
                    if vals and len(vals) <= 80:
                        picked = st.multiselect(f"{col_name}", options=vals, default=[])
                        if picked:
                            advanced_equals[col_name] = picked

        xlsx_selections = pontos_to_xlsx_selection(effective_selected_pontos, vars_sel)
        st.session_state["xlsx_selections"] = xlsx_selections
        st.session_state["xlsx_selections_json"] = json.dumps(xlsx_selections, ensure_ascii=False)
        st.markdown("**Selecao XLSX derivada (ponto_id -> equipamento/variaveis)**")
        st.caption(f"JSON selecao XLSX: `{st.session_state['xlsx_selections_json']}`")

        where_sql, where_params = build_filters(
            equips_selected=equips_selected,
            equip_like=None,
            vars_sel=vars_sel,
            se_sel=se_sel if "SE" in col_names else None,
            bay_sel=bay_sel if "BAY" in col_names else None,
            equipamento_sel=equips_selected if "EQUIPAMENTO" in col_names else None,
            terminal_sel=terminal_sel if "TERMINAL" in col_names else None,
            # --- CHANGED: evita lista gigante de ponto_id; filtros de contexto ja definem o recorte ---
            ponto_ids_sel=None,
            ponto_id_like=ponto_id_search,
            advanced_equals=advanced_equals,
            advanced_ranges=advanced_ranges,
            ano=ano,
            mes=mes,
            t0=None,
            t1=None,
        )

        if "page" not in st.session_state:
            st.session_state.page = 1
        colnav1, colnav2, _ = st.columns([1, 1, 3])
        with colnav1:
            if st.button("Pagina anterior"):
                st.session_state.page = max(1, st.session_state.page - 1)
        with colnav2:
            if st.button("Proxima pagina"):
                st.session_state.page = st.session_state.page + 1

        offset = (st.session_state.page - 1) * page_size
        pagination_sql, pagination_params = build_pagination(page_size, offset)
        total, df_page = query_page(
            db_path,
            where_sql,
            where_params,
            pagination_sql=pagination_sql,
            pagination_params=pagination_params,
            order_sql=order_sql,
        )
        total_pages = max(1, math.ceil(total / page_size))
        st.write(
            f"**Total de linhas no recorte:** {total:,} | "
            f"**Pagina:** {st.session_state.page}/{total_pages} | **Offset:** {offset}"
        )
        if int(total) >= int(PERFORMANCE_WARN_ROWS):
            st.warning("Recorte muito grande. A consulta pode ficar lenta; use filtros adicionais.")
        if not cfg.is_prod:
            st.caption(
                "Debug filtros: "
                f"selected_pontos_effective={len(effective_selected_pontos)}, "
                f"equips_selected={len(equips_selected)}"
            )
        st.dataframe(df_page, width="stretch", height=520)
        st.download_button(
            label="Baixar esta pagina em CSV",
            data=df_page.to_csv(index=False).encode("utf-8"),
            file_name=f"andys_page_{st.session_state.page}.csv",
            mime="text/csv",
        )

        st.divider()
        st.subheader("Exportar com base nos filtros do app")
        if not user_ctx.can_export:
            st.info("Seu perfil e de leitura. Exportacao indisponivel.")

        export_cap = st.number_input(
            "Limite de linhas para exportacao (0 = sem limite)",
            min_value=0,
            value=0,
            step=100000,
            disabled=not user_ctx.can_export,
        )
        limit_cap = None if export_cap == 0 else int(export_cap)

        with st.expander("Configuracoes do Dashboard XLSX"):
            agg = st.selectbox("Agregacao", ["max", "last"], index=0, disabled=not user_ctx.can_export, key="agg_select")
            time_floor = st.text_input(
                "Time floor (opcional)", value="", help="Ex: 15min, 1H, 1D", disabled=not user_ctx.can_export, key="time_floor_input"
            )
            max_timestamps = st.number_input(
                "Max timestamps no XLSX",
                min_value=1000,
                value=int(XLSX_MAX_TIMESTAMPS_DEFAULT),
                step=50000,
                disabled=not user_ctx.can_export,
                key="max_timestamps_input",
            )
            equip_slots = st.number_input("Slots de equipamento", min_value=1, value=8, step=1, disabled=not user_ctx.can_export)
            var_slots = st.number_input("Slots de variavel", min_value=1, value=6, step=1, disabled=not user_ctx.can_export)

        st.markdown("### Auditoria de Exportacao")
        audit_format = st.selectbox(
            "Tipo de export para auditar",
            options=["xlsx_dashboard", "csv_long", "csv_wide"],
            format_func=lambda x: {
                "xlsx_dashboard": "XLSX Dashboard",
                "csv_long": "CSV LONG",
                "csv_wide": "CSV WIDE",
            }[x],
            key="audit_format_select",
        )
        destination_excel = st.checkbox(
            "Pretendo abrir este arquivo no Excel",
            value=True if audit_format != "csv_long" else False,
            key="audit_destination_excel",
        )
        run_audit_btn = st.button("Rodar auditoria", key="run_export_audit_btn")

        def _run_export_audit(
            *,
            target_format: str,
            target_destination_excel: bool,
            action_taken: Optional[str] = None,
        ) -> Dict[str, Any]:
            intent = ExportIntent(
                format=target_format,  # type: ignore[arg-type]
                include_metadata=True,
                destination_excel=bool(target_destination_excel),
                agg=str(agg),
                time_floor=(str(time_floor).strip() or None),
                max_timestamps=int(max_timestamps),
            )
            con = get_cur(db_path)
            metrics = estimate_export_shape(
                con=con,
                where_sql=where_sql,
                where_params=where_params,
                intent=intent,
            )
            findings = run_audit(metrics=metrics, intent=intent)
            result = {
                "intent": intent,
                "metrics": metrics,
                "findings": findings,
            }
            st.session_state["export_audit_result"] = result
            audit_export_risk(
                user_id=user_ctx.user_id,
                role=user_ctx.role,
                intent={
                    "format": intent.format,
                    "destination_excel": intent.destination_excel,
                },
                filters=_sanitize_audit_filters(
                    t0=period_t0,
                    t1=period_t1,
                    equips_selected=_equip_ids_from_pontos(effective_selected_pontos),
                    vars_sel=vars_sel,
                    agg=agg,
                    time_floor=time_floor,
                    max_timestamps=int(max_timestamps),
                ),
                metrics=metrics,
                findings=_serialize_findings(findings),
                action_taken=action_taken,
                audit_log_path=cfg.audit_log_path,
            )
            return result

        if run_audit_btn:
            _run_export_audit(
                target_format=str(audit_format),
                target_destination_excel=bool(destination_excel),
            )

        audit_result = st.session_state.get("export_audit_result")
        hard_stop_xlsx = False
        warn_or_soft_error = False
        if audit_result:
            intent_obj: ExportIntent = audit_result["intent"]
            metrics = audit_result["metrics"]
            findings = audit_result["findings"]
            status = _risk_status(findings)
            c_a1, c_a2, c_a3, c_a4 = st.columns(4)
            c_a1.metric("Timestamps estimados", f"{int(metrics.get('estimated_rows_wide', 0)):,}")
            c_a2.metric("Linhas LONG estimadas", f"{int(metrics.get('estimated_rows_long', 0)):,}")
            c_a3.metric("Series estimadas", f"{int(metrics.get('estimated_series', 0)):,}")
            c_a4.metric("Span (dias)", f"{float(metrics.get('time_span_days', 0.0)):.1f}")
            if status == "ERROR":
                st.error("Status de risco: ERROR")
            elif status == "WARN":
                st.warning("Status de risco: WARN")
            else:
                st.info("Status de risco: OK")

            for f in findings:
                msg = f"[{f.code}] {f.title} - {f.details}"
                if f.severity == "ERROR":
                    st.error(msg)
                elif f.severity == "WARN":
                    st.warning(msg)
                else:
                    st.info(msg)

            if user_ctx.is_admin and (not cfg.is_prod or cfg.admin_diag_enabled):
                with st.expander("Diagnostico avancado da auditoria"):
                    st.json(
                        {
                            "intent": {
                                "format": intent_obj.format,
                                "destination_excel": intent_obj.destination_excel,
                                "agg": intent_obj.agg,
                                "time_floor": intent_obj.time_floor,
                            },
                            "metrics": metrics,
                            "where_sql_preview": where_sql[:240],
                        }
                    )

            rec_actions: Dict[str, Any] = {}
            for f in findings:
                for ra in f.recommended_actions:
                    rec_actions[ra.id] = ra
            if rec_actions:
                st.markdown("**Recomendacoes acionaveis**")
                for action_id, ra in rec_actions.items():
                    if st.button(f"Aplicar: {ra.label}", key=f"audit_action_{action_id}"):
                        state_in = {
                            "t0": st.session_state.get("t0_input", ""),
                            "t1": st.session_state.get("t1_input", ""),
                            "time_floor": st.session_state.get("time_floor_input", ""),
                            "agg": st.session_state.get("agg_select", "max"),
                            "max_timestamps": int(st.session_state.get("max_timestamps_input", int(XLSX_MAX_TIMESTAMPS_DEFAULT))),
                        }
                        updated = apply_recommendation(state_in, action_id)
                        st.session_state["t0_input"] = str(updated.get("t0", state_in["t0"]))
                        st.session_state["t1_input"] = str(updated.get("t1", state_in["t1"]))
                        st.session_state["time_floor_input"] = str(updated.get("time_floor", state_in["time_floor"]))
                        st.session_state["agg_select"] = str(updated.get("agg", state_in["agg"]))
                        st.session_state["max_timestamps_input"] = int(updated.get("max_timestamps", state_in["max_timestamps"]))
                        _run_export_audit(
                            target_format=str(audit_format),
                            target_destination_excel=bool(destination_excel),
                            action_taken=f"apply:{action_id}",
                        )
                        st.rerun()

            if intent_obj.format == "xlsx_dashboard":
                hard_stop_xlsx = any(f.severity == "ERROR" and bool(f.hard_stop) for f in findings)
            warn_or_soft_error = any(
                (f.severity == "WARN") or (f.severity == "ERROR" and not bool(f.hard_stop))
                for f in findings
            )

        recent_events = read_recent_audit_events(
            audit_log_path=cfg.audit_log_path,
            event_type="export_audit",
            limit=10,
        )
        with st.expander("Ultimos eventos de auditoria de exportacao"):
            if recent_events:
                st.dataframe(pd.DataFrame(recent_events), width="stretch", height=240)
            else:
                st.caption("Sem eventos recentes.")

        confirm_risk = st.checkbox(
            "Entendo o risco e desejo exportar mesmo assim",
            value=False,
            key="confirm_export_risk",
        )

        colx1, colx2, colx3 = st.columns([1, 1, 1])
        with colx1:
            export_long = st.button("Exportar CSV (LONG completo)", type="primary", disabled=not user_ctx.can_export)
        with colx2:
            export_wide = st.button("Exportar CSV (WIDE timestamp x series)", disabled=not user_ctx.can_export)
        with colx3:
            export_xlsx = st.button("Gerar XLSX Dashboard (motor BI)", disabled=(not user_ctx.can_export) or hard_stop_xlsx)

        if export_long or export_wide or export_xlsx:
            if not user_ctx.can_export:
                raise PermissionError("Perfil sem permissao de exportacao.")
            selected_format = "csv_long" if export_long else ("csv_wide" if export_wide else "xlsx_dashboard")
            current_audit = _run_export_audit(
                target_format=selected_format,
                target_destination_excel=bool(destination_excel),
                action_taken="pre_export_check",
            )
            findings = current_audit["findings"]
            has_hard_stop = any(f.severity == "ERROR" and bool(f.hard_stop) for f in findings)
            has_warn_or_soft_error = any(
                (f.severity == "WARN") or (f.severity == "ERROR" and not bool(f.hard_stop))
                for f in findings
            )
            if has_hard_stop:
                raise ValueError("Exportacao bloqueada pela auditoria: limite fisico excedido para este formato.")
            if has_warn_or_soft_error and not confirm_risk:
                raise ValueError("Auditoria indica risco. Marque a confirmacao para exportar mesmo assim.")
            if has_warn_or_soft_error:
                audit_export_risk(
                    user_id=user_ctx.user_id,
                    role=user_ctx.role,
                    intent={"format": selected_format, "decision": "forced_export"},
                    filters=_sanitize_audit_filters(
                        t0=period_t0,
                        t1=period_t1,
                        equips_selected=_equip_ids_from_pontos(effective_selected_pontos),
                        vars_sel=vars_sel,
                        agg=agg,
                        time_floor=time_floor,
                        max_timestamps=int(max_timestamps),
                    ),
                    metrics=current_audit["metrics"],
                    findings=_serialize_findings(findings),
                    action_taken="force_export_confirmed",
                    audit_log_path=cfg.audit_log_path,
                )
            equips_for_export = _equip_ids_from_pontos(effective_selected_pontos)
            if not effective_selected_pontos:
                raise ValueError("Para exportar, selecione ao menos 1 ponto (ponto_id).")
            ensure_dir(export_dir)
            with st.spinner("Extraindo recorte completo do lake (pode levar alguns segundos)..."):
                df_long = query_full_long(db_path, where_sql, where_params, limit_cap=limit_cap)
            if df_long.empty:
                raise ValueError("Recorte vazio: ajuste filtros (equip/tempo/vars).")

            export_filters = {
                "ano": ano,
                "mes": mes,
                "se": se_sel,
                "bay": bay_sel,
                "equips_selected": equips_selected,
                "selected_pontos": effective_selected_pontos,
                "terminal_sel": terminal_sel,
                "vars_sel": vars_sel,
                "ponto_id_like": ponto_id_search,
                "t0": period_t0,
                "t1": period_t1,
            }

            if export_long:
                out_path = os.path.join(export_dir, "andys_export_long.csv")
                df_long.to_csv(out_path, index=False, encoding="utf-8")
                audit_export(
                    user_id=user_ctx.user_id,
                    role=user_ctx.role,
                    rowcount=len(df_long),
                    filters=export_filters,
                    file_path=out_path,
                    audit_log_path=cfg.audit_log_path,
                )
                st.success("CSV LONG exportado com sucesso.")
                if not cfg.is_prod:
                    st.caption(f"Arquivo: {out_path}")

            if export_wide:
                df_tmp = df_long.copy()
                df_tmp["timestamp"] = pd.to_datetime(df_tmp["timestamp"], errors="coerce")
                df_tmp = df_tmp.dropna(subset=["timestamp", "EQUIPAMENTO", "var"])
                wide = (
                    df_tmp.pivot_table(
                        index=["timestamp", "SE", "BAY", "EQUIPAMENTO", "TERMINAL", "ponto_id"],
                        columns="var",
                        values="valor",
                        aggfunc="last",
                    )
                    .reset_index()
                )
                out_path = os.path.join(export_dir, "andys_export_wide.csv")
                wide.to_csv(out_path, index=False, encoding="utf-8")
                audit_export(
                    user_id=user_ctx.user_id,
                    role=user_ctx.role,
                    rowcount=len(wide),
                    filters=export_filters,
                    file_path=out_path,
                    audit_log_path=cfg.audit_log_path,
                )
                st.success("CSV WIDE exportado com sucesso.")
                if not cfg.is_prod:
                    st.caption(f"Arquivo: {out_path}")

            if export_xlsx:
                if BI_IMPORT_ERROR is not None or aggregate_long is None or construir_bi_excel_multi_equip_multi_var_long is None:
                    raise RuntimeError("Motor BI indisponivel no servidor.")
                if not effective_selected_pontos:
                    raise ValueError("No XLSX, selecione ao menos 1 ponto.")
                if not vars_sel:
                    raise ValueError("No XLSX, selecione ao menos 1 variavel.")

                selections = normalize_selections(st.session_state.get("xlsx_selections", {}))
                missing_cfg = [e for e in equips_for_export if e not in selections]
                empty_vars = [e for e in equips_for_export if not selections.get(e)]
                if missing_cfg or empty_vars:
                    pending = sorted(set(missing_cfg + empty_vars))
                    st.warning("Selecione ao menos 1 variavel para cada equipamento antes de gerar o XLSX.")
                    st.caption("Equipamentos pendentes: " + ", ".join(pending[:12]))
                    st.stop()
                validate_selections(selections, required_equips=equips_for_export)
                selected_pairs = expand_pairs(selections)
                if not selected_pairs:
                    raise ValueError("Selecione ao menos 1 par equipamento/variavel para o XLSX.")

                df_input = _normalize_for_agg(df_long)
                df_agg = aggregate_long(df_input, agg=agg, time_floor=(time_floor.strip() or None))
                df_agg = _normalize_agg_schema(df_agg)
                keep_pairs = {(eq, vv) for eq, vv in selected_pairs}
                pair_idx = pd.MultiIndex.from_frame(df_agg[["_EQUIP", "_VAR"]].astype(str))
                df_agg = df_agg[pair_idx.isin(list(keep_pairs))].copy()
                if df_agg.empty:
                    preview_keys = sorted(df_input["equip_id"].astype(str).unique().tolist())[:8]
                    st.error("Apos agregacao, o recorte ficou vazio para os pares selecionados.")
                    st.caption("Verifique periodo, variaveis e agregacao/time_floor.")
                    st.caption("Exemplos de equipamentos disponiveis no recorte: " + ", ".join(preview_keys))
                    st.stop()

                out_path = os.path.join(export_dir, "andys_dashboard.xlsx")
                report_meta = {
                    "equips": ", ".join(sorted(selections.keys())),
                    "t0": period_t0,
                    "t1": period_t1,
                    "vars": "; ".join([f"{eq}:[{', '.join(vs)}]" for eq, vs in selections.items()]),
                    "selected_ponto_ids": json.dumps(effective_selected_pontos, ensure_ascii=False),
                    "agg": agg,
                    "time_floor": time_floor.strip() or "(none)",
                    "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                try:
                    out_file, warns = _call_xlsx_engine(
                        df_agg=df_agg,
                        out_path=out_path,
                        equip_slots=int(equip_slots),
                        var_slots=int(var_slots),
                        max_timestamps=int(max_timestamps),
                        report_meta=report_meta,
                        selected_pairs=selected_pairs,
                    )
                except PermissionError:
                    alt_name = f"andys_dashboard_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    out_file, warns = _call_xlsx_engine(
                        df_agg=df_agg,
                        out_path=os.path.join(export_dir, alt_name),
                        equip_slots=int(equip_slots),
                        var_slots=int(var_slots),
                        max_timestamps=int(max_timestamps),
                        report_meta=report_meta,
                        selected_pairs=selected_pairs,
                    )
                audit_export(
                    user_id=user_ctx.user_id,
                    role=user_ctx.role,
                    rowcount=len(df_agg),
                    filters=export_filters,
                    file_path=out_file,
                    audit_log_path=cfg.audit_log_path,
                )
                st.success("XLSX Dashboard gerado com sucesso.")
                for w in warns:
                    if not cfg.is_prod:
                        st.warning(f"[WARN] {w}")
                if not cfg.is_prod:
                    st.caption(f"Arquivo: {out_file}")

        st.caption("Pronto: exportacoes sempre seguem os filtros do app.")
    except Exception as exc:
        if cfg is None:
            is_prod = os.environ.get("ANDYS_ENV", "dev").strip().lower() == "prod"
            log_exception(exc, cid, {"module": "andys_table_app", "phase": "bootstrap"})
            st.error(handle_user_error(exc, cid, is_prod))
            return
        _show_error(exc, cfg, cid, {"module": "andys_table_app"})


if __name__ == "__main__":
    main()
