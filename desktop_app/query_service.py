from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import pandas as pd

from db.query_builder import (
    build_distinct_query,
    build_filters,
    build_order_by,
    build_pagination,
    build_ponto_query,
    build_vars_for_context_query,
)
from measurement_value import normalize_measurement_series

from desktop_app.models import PageResult, QueryFilters


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


# --- NEW: desktop read-only query service extracted from Streamlit app behavior ---
class DesktopQueryService:
    def __init__(self, db_path: str) -> None:
        self.db_path = str(db_path)

    # --- NEW: isolated DuckDB cursor to keep desktop queries stateless and predictable ---
    def _connect(self) -> duckdb.DuckDBPyConnection:
        con = duckdb.connect(self.db_path, read_only=True)
        con.execute("PRAGMA threads=4;")
        return con

    # --- NEW: desktop health check before enabling the operational screen ---
    def validate_ready(self) -> None:
        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"DuckDB nao encontrado em: {self.db_path}")
        con = self._connect()
        try:
            tables = {str(r[0]).lower() for r in con.execute("SHOW TABLES;").fetchall()}
        finally:
            con.close()
        if "medicoes" not in tables:
            raise RuntimeError("DuckDB encontrado, mas a tabela/view 'medicoes' nao existe.")

    # --- NEW: schema inspection reused across query helpers ---
    def get_medicoes_columns(self) -> List[Tuple[str, str]]:
        con = self._connect()
        try:
            rows = con.execute("DESCRIBE SELECT * FROM medicoes;").fetchall()
        finally:
            con.close()
        return [(str(r[0]), str(r[1])) for r in rows]

    # --- NEW: safe column-set helper extracted from Streamlit query path ---
    def _column_set(self) -> set[str]:
        return {c for c, _ in self.get_medicoes_columns()}

    # --- NEW: quote identifier for ad hoc aggregate probes ---
    def _quote_ident(self, name: str) -> str:
        return '"' + str(name).replace('"', '""') + '"'

    # --- NEW: stable projection so desktop table works even with reduced catalog schemas ---
    def _projected_base_select(self) -> str:
        cols = self._column_set()

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

    # --- NEW: overview data used by the desktop summary/status panels ---
    def load_overview(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        con = self._connect()
        try:
            overview = con.execute(
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

            by_month = con.execute(
                """
                SELECT ano, mes, COUNT(*) AS rows
                FROM medicoes
                GROUP BY ano, mes
                ORDER BY ano, mes;
                """
            ).df()

            vars_df = con.execute(
                """
                SELECT var, classe, COUNT(*) AS rows
                FROM medicoes
                GROUP BY var, classe
                ORDER BY rows DESC;
                """
            ).df()

            top_equips = con.execute(
                """
                SELECT equip_id, COUNT(*) AS rows, MIN(timestamp) AS ts_min, MAX(timestamp) AS ts_max
                FROM medicoes
                GROUP BY equip_id
                ORDER BY rows DESC
                LIMIT 50;
                """
            ).df()
        finally:
            con.close()
        return overview, by_month, vars_df, top_equips

    # --- NEW: ingestion metadata reused in the desktop status screen ---
    def load_ingestion_metadata(self, lake_root: str) -> Tuple[Dict[str, Any], pd.DataFrame]:
        cfg_path = Path(lake_root) / "andys_config.json"
        manifest_path = Path(lake_root) / "manifest.json"

        cfg: Dict[str, Any] = {}
        files_df = pd.DataFrame(columns=["file", "indexed_at", "source_size", "source_mtime", "rows_long"])

        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            rows: List[Dict[str, Any]] = []
            for key, value in (manifest.get("files") or {}).items():
                rows.append(
                    {
                        "file": key,
                        "indexed_at": value.get("indexed_at"),
                        "source_size": value.get("source_size"),
                        "source_mtime": value.get("source_mtime"),
                        "rows_long": value.get("rows_long"),
                    }
                )
            files_df = pd.DataFrame(rows).sort_values("indexed_at", ascending=False) if rows else files_df

        return cfg, files_df

    # --- NEW: canonical month normalization shared by desktop filters ---
    @staticmethod
    def normalize_month_int(value: object) -> Optional[int]:
        try:
            month = int(str(value).strip())
        except Exception:
            return None
        if 1 <= month <= 12:
            return month
        return None

    # --- NEW: latest year/month default reused by the desktop first-load flow ---
    @staticmethod
    def latest_available_year_month(by_month: pd.DataFrame) -> Tuple[int, int]:
        if by_month.empty:
            raise ValueError("Sem dados de ano/mes para selecionar padrao.")
        pairs = [
            (int(row.ano), int(row.mes))
            for row in by_month[["ano", "mes"]].itertuples(index=False)
            if DesktopQueryService.normalize_month_int(row.mes) is not None
        ]
        if not pairs:
            raise ValueError("Sem pares de ano/mes validos em medicoes.")
        return max(pairs, key=lambda p: (p[0], p[1]))

    # --- NEW: list valid months for the selected year in the desktop UI ---
    @staticmethod
    def months_for_year(by_month: pd.DataFrame, year: int) -> List[int]:
        if by_month.empty:
            return []
        return sorted(
            {
                int(m)
                for m in by_month[by_month["ano"] == int(year)]["mes"].tolist()
                if DesktopQueryService.normalize_month_int(m) is not None
            }
        )

    # --- NEW: derive inclusive bounds for multi-month desktop filtering/export ---
    @staticmethod
    def month_selection_bounds(ano: int, meses_sel: List[int]) -> Tuple[str, str]:
        meses_norm = sorted({int(m) for m in meses_sel})
        if not meses_norm:
            raise ValueError("Selecione ao menos um mes.")
        start = pd.Timestamp(int(ano), int(meses_norm[0]), 1, 0, 0, 0)
        if int(meses_norm[-1]) == 12:
            next_month = pd.Timestamp(int(ano) + 1, 1, 1, 0, 0, 0)
        else:
            next_month = pd.Timestamp(int(ano), int(meses_norm[-1]) + 1, 1, 0, 0, 0)
        end = next_month - pd.Timedelta(seconds=1)
        return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")

    # --- NEW: normalize month list inputs from the desktop multiselect widgets ---
    @staticmethod
    def _coerce_meses_sel(meses_sel: List[int]) -> Tuple[int, ...]:
        normalized = [m for m in (DesktopQueryService.normalize_month_int(v) for v in meses_sel) if m is not None]
        return tuple(dict.fromkeys(normalized))

    # --- NEW: shared WHERE clause builder for page/export/audit queries ---
    def build_where(self, filters: QueryFilters) -> Tuple[str, Tuple[object, ...]]:
        return build_filters(
            equips_selected=filters.equipamento_sel,
            equip_like=None,
            vars_sel=filters.vars_sel,
            se_sel=filters.se_sel,
            bay_sel=filters.bay_sel,
            equipamento_sel=filters.equipamento_sel,
            terminal_sel=filters.terminal_sel,
            ponto_ids_sel=None,
            ponto_id_like=filters.ponto_id_like,
            advanced_equals=filters.advanced_equals,
            advanced_ranges=filters.advanced_ranges,
            ano=filters.ano,
            mes=None,
            meses_sel=list(self._coerce_meses_sel(filters.meses_sel)),
            t0=None,
            t1=None,
        )

    # --- NEW: desktop filter option loader extracted from the Streamlit sidebar flow ---
    def load_distinct_options(
        self,
        *,
        target_col: str,
        filters: QueryFilters,
        limit: int = 500,
    ) -> List[str]:
        con = self._connect()
        try:
            meses_norm = self._coerce_meses_sel(filters.meses_sel)
            mes_single = int(meses_norm[0]) if len(meses_norm) == 1 else None
            meses_many = list(meses_norm) if len(meses_norm) > 1 else None
            sql, params = build_distinct_query(
                target_col=target_col,
                ano=filters.ano,
                mes=mes_single,
                meses_sel=meses_many,
                t0=None,
                t1=None,
                se_sel=list(filters.se_sel),
                bay_sel=list(filters.bay_sel),
                equipamento_sel=list(filters.equipamento_sel),
                terminal_sel=list(filters.terminal_sel),
                ponto_id_like=filters.ponto_id_like,
                limit=limit,
                include_empty=(target_col == "BAY"),
            )
            out: List[str] = []
            for row in con.execute(sql, params).fetchall():
                val = row[0]
                if val is None:
                    continue
                sval = str(val)
                if target_col != "BAY" and not sval.strip():
                    continue
                out.append(sval)
            return out
        finally:
            con.close()

    # --- NEW: desktop point resolver used for diagnostics and XLSX context ---
    def resolve_points(self, filters: QueryFilters, *, limit: int = 500) -> List[str]:
        con = self._connect()
        try:
            meses_norm = self._coerce_meses_sel(filters.meses_sel)
            mes_single = int(meses_norm[0]) if len(meses_norm) == 1 else None
            meses_many = list(meses_norm) if len(meses_norm) > 1 else None
            sql, params = build_ponto_query(
                ano=filters.ano,
                mes=mes_single,
                meses_sel=meses_many,
                se_sel=list(filters.se_sel),
                bay_sel=list(filters.bay_sel),
                equipamento_sel=list(filters.equipamento_sel),
                terminal_sel=list(filters.terminal_sel),
                ponto_id_like=filters.ponto_id_like,
                limit=limit,
            )
            return [str(r[0]) for r in con.execute(sql, params).fetchall() if r[0] is not None]
        finally:
            con.close()

    # --- NEW: variable discovery by current context without enumerating all rows in the UI ---
    def load_vars_by_context(self, filters: QueryFilters) -> List[str]:
        con = self._connect()
        try:
            meses_norm = self._coerce_meses_sel(filters.meses_sel)
            mes_single = int(meses_norm[0]) if len(meses_norm) == 1 else None
            if len(meses_norm) > 1:
                sql, params = build_vars_for_context_query(
                    ano=filters.ano,
                    mes=None,
                    meses_sel=list(meses_norm),
                    se_sel=list(filters.se_sel),
                    bay_sel=list(filters.bay_sel),
                    equipamento_sel=list(filters.equipamento_sel),
                    terminal_sel=list(filters.terminal_sel),
                    ponto_id_like=filters.ponto_id_like,
                )
            else:
                sql, params = build_vars_for_context_query(
                    ano=filters.ano,
                    mes=mes_single,
                    se_sel=list(filters.se_sel),
                    bay_sel=list(filters.bay_sel),
                    equipamento_sel=list(filters.equipamento_sel),
                    terminal_sel=list(filters.terminal_sel),
                    ponto_id_like=filters.ponto_id_like,
                )
            return [str(r[0]) for r in con.execute(sql, params).fetchall() if str(r[0]).strip()]
        finally:
            con.close()

    # --- NEW: paginated query result for the desktop table view ---
    def query_page(
        self,
        *,
        filters: QueryFilters,
        page_size: int,
        page_number: int,
        order_label: str,
    ) -> PageResult:
        where_sql, where_params = self.build_where(filters)
        sort_key, sort_dir = ORDER_OPTIONS[order_label]
        order_sql = build_order_by(sort_key, sort_dir, ORDER_ALLOWLIST)
        offset = max(int(page_number) - 1, 0) * int(page_size)
        pagination_sql, pagination_params = build_pagination(int(page_size), int(offset))
        con = self._connect()
        try:
            select_projection = self._projected_base_select()
            count_row = con.execute(
                f"SELECT COUNT(*) AS n FROM medicoes WHERE {where_sql};",
                where_params,
            ).fetchone()
            if count_row is None:
                raise RuntimeError(f"COUNT(*) retornou vazio para where_sql={where_sql!r}")
            total = int(count_row[0] or 0)
            df = con.execute(
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
        finally:
            con.close()
        if "valor" in df.columns:
            df["valor"] = normalize_measurement_series(df["valor"], ndigits=1)
        return PageResult(total=total, frame=df)

    # --- NEW: full recorte loader reused by desktop export actions ---
    def query_full_long(self, *, filters: QueryFilters, limit_cap: Optional[int] = None) -> pd.DataFrame:
        where_sql, where_params = self.build_where(filters)
        con = self._connect()
        try:
            select_projection = self._projected_base_select()
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
            df = con.execute(sql, params).df()
        finally:
            con.close()
        if "valor" in df.columns:
            df["valor"] = normalize_measurement_series(df["valor"], ndigits=1)
        return df

    # --- NEW: ad hoc numeric range probe for future desktop advanced-filter UX ---
    def get_numeric_range(self, col: str) -> Tuple[Optional[float], Optional[float]]:
        col_q = self._quote_ident(col)
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
        con = self._connect()
        try:
            row = con.execute(q).fetchone()
        except Exception:
            logging.warning("Falha ao calcular range numerico para coluna '%s'. Ignorando.", col)
            return None, None
        finally:
            con.close()
        if row is None:
            return None, None
        lo = float(row[0]) if row[0] is not None else None
        hi = float(row[1]) if row[1] is not None else None
        return lo, hi
