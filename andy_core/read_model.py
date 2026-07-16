from __future__ import annotations

import logging
from typing import Any, Iterable, Optional, Sequence, Tuple

import pandas as pd

from measurement_value import normalize_measurement_series


def column_set(columns: Sequence[Tuple[str, str]]) -> set[str]:
    return {str(name) for name, _dtype in columns}


def quote_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def is_safe_filter_col(name: str) -> bool:
    return str(name).replace("_", "").isalnum()


def projected_base_select(columns: Sequence[Tuple[str, str]] | Iterable[str]) -> str:
    cols = set(columns) if not isinstance(columns, Sequence) or (columns and not isinstance(next(iter(columns)), tuple)) else {str(name) for name, _dtype in columns}  # type: ignore[arg-type]

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
    for optional_col in ["BAY_RAW", "EQUIPAMENTO_RAW", "context_bay_source"]:
        if optional_col in cols:
            select_items.append(pick(optional_col))
    return ", ".join(select_items)


def normalize_measurement_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if "valor" in frame.columns:
        frame["valor"] = normalize_measurement_series(frame["valor"], ndigits=1)
    return frame


def run_query_page(
    executor: Any,
    *,
    select_projection: str,
    where_sql: str,
    where_params: Tuple[object, ...],
    pagination_sql: str,
    pagination_params: Tuple[int, int],
    order_sql: str,
) -> Tuple[int, pd.DataFrame]:
    count_row = executor.execute(
        f"SELECT COUNT(*) AS n FROM medicoes WHERE {where_sql};",
        where_params,
    ).fetchone()
    if count_row is None:
        raise RuntimeError(f"COUNT(*) retornou vazio para where_sql={where_sql!r}")
    total = int(count_row[0] or 0)
    frame = executor.execute(
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
    return total, normalize_measurement_frame(frame)


def run_query_full_long(
    executor: Any,
    *,
    select_projection: str,
    where_sql: str,
    where_params: Tuple[object, ...],
    limit_cap: Optional[int] = None,
) -> pd.DataFrame:
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
    frame = executor.execute(sql, params).df()
    return normalize_measurement_frame(frame)


def get_numeric_range(
    executor: Any,
    col: str,
    *,
    warning_logger: Optional[logging.Logger] = None,
    warning_message: str = "Falha ao calcular range numerico para coluna '%s'. Ignorando.",
) -> Tuple[Optional[float], Optional[float]]:
    col_q = quote_ident(col)
    query = (
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
        row = executor.execute(query).fetchone()
    except Exception:
        if warning_logger is not None:
            warning_logger.warning(warning_message, col)
        return None, None
    if row is None:
        return None, None
    lo = float(row[0]) if row[0] is not None else None
    hi = float(row[1]) if row[1] is not None else None
    return lo, hi
