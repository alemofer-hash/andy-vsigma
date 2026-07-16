from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
from typing import Any, Dict, Iterable, List, Literal, Optional

import duckdb

from config import (
    EXCEL_MAX_ROWS,
    EXCEL_SAFE_HEADROOM,
    FILESIZE_WARN_MB,
    PERFORMANCE_WARN_ROWS,
    TIME_SUGGESTION_BUCKETS,
    XLSX_MAX_TIMESTAMPS_DEFAULT,
)


ExportFormat = Literal["csv_long", "csv_wide", "xlsx_dashboard"]


@dataclass(frozen=True)
class RecommendedAction:
    id: str
    label: str
    patch: Dict[str, Any]
    explanation: str


@dataclass(frozen=True)
class ExportIntent:
    format: ExportFormat
    include_metadata: bool = True
    destination_excel: bool = False
    agg: str = "max"
    time_floor: Optional[str] = None
    max_timestamps: int = XLSX_MAX_TIMESTAMPS_DEFAULT


@dataclass(frozen=True)
class AuditFinding:
    code: str
    severity: Literal["INFO", "WARN", "ERROR"]
    title: str
    details: str
    recommended_actions: List[RecommendedAction]
    hard_stop: bool = False


def _colset(con: duckdb.DuckDBPyConnection) -> set[str]:
    rows = con.execute("DESCRIBE SELECT * FROM medicoes;").fetchall()
    return {str(r[0]) for r in rows}


def _equip_expr(cols: set[str]) -> str:
    if "ponto_id" in cols:
        return "NULLIF(CAST(ponto_id AS VARCHAR), '')"
    if "equip_id" in cols:
        return "CAST(equip_id AS VARCHAR)"
    if "EQUIPAMENTO" in cols:
        return "CAST(EQUIPAMENTO AS VARCHAR)"
    return "CAST('' AS VARCHAR)"


def _var_expr(cols: set[str]) -> str:
    if "var" in cols:
        return "CAST(var AS VARCHAR)"
    return "CAST('' AS VARCHAR)"


def _estimate_filesize_mb(intent: ExportIntent, rows_long: int, rows_wide: int, series: int) -> float:
    s = max(series, 1)
    if intent.format == "csv_long":
        raw_bytes = rows_long * 64
    elif intent.format == "csv_wide":
        raw_bytes = rows_wide * (32 + s * 16)
    else:
        raw_bytes = rows_wide * (48 + s * 24)
    return round(raw_bytes / (1024 * 1024), 1)


def _suggested_timefloor(span_days: float) -> Optional[str]:
    for min_days, floor in TIME_SUGGESTION_BUCKETS:
        if span_days >= min_days:
            return floor
    return None


def _build_recommendations(
    min_ts: Optional[dt.datetime],
    max_ts: Optional[dt.datetime],
    intent: ExportIntent,
) -> List[RecommendedAction]:
    recs: List[RecommendedAction] = []
    if max_ts is None:
        now = dt.datetime.now()
    else:
        now = max_ts
    for days in [30, 90, 365]:
        recs.append(
            RecommendedAction(
                id=f"set_last_{days}d",
                label=f"Recortar para ultimos {days} dias",
                patch={
                    "t0": (now - dt.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S"),
                    "t1": now.strftime("%Y-%m-%d %H:%M:%S"),
                },
                explanation=f"Reduz volume mantendo janela recente ({days} dias).",
            )
        )

    if min_ts and max_ts:
        span_days = max((max_ts - min_ts).total_seconds() / 86400.0, 0.0)
        floor = _suggested_timefloor(span_days)
        if floor:
            recs.append(
                RecommendedAction(
                    id=f"set_timefloor_{floor.lower()}",
                    label=f"Aplicar timefloor {floor}",
                    patch={"time_floor": floor},
                    explanation="Downsample para reduzir timestamps e tamanho de export.",
                )
            )
    recs.append(
        RecommendedAction(
            id="set_agg_last",
            label="Trocar agregacao para last",
            patch={"agg": "last"},
            explanation="Agregacao last geralmente reduz ruido em series densas.",
        )
    )
    if intent.format == "xlsx_dashboard":
        recs.append(
            RecommendedAction(
                id="set_max_ts_safe",
                label=f"Limitar max_timestamps para {XLSX_MAX_TIMESTAMPS_DEFAULT:,}",
                patch={"max_timestamps": XLSX_MAX_TIMESTAMPS_DEFAULT},
                explanation="Evita XLSX com blocos excessivos para o Excel.",
            )
        )
    recs.append(
        RecommendedAction(
            id="reduce_selection_hint",
            label="Reduzir equipamentos/variaveis selecionados",
            patch={"selection_hint": True},
            explanation="Diminuir series reduz drasticamente o peso da exportacao.",
        )
    )
    return recs


def estimate_export_shape(
    *,
    con: duckdb.DuckDBPyConnection,
    where_sql: str,
    where_params: Iterable[object],
    intent: ExportIntent,
) -> Dict[str, Any]:
    cols = _colset(con)
    equip_expr = _equip_expr(cols)
    var_expr = _var_expr(cols)
    row = con.execute(
        f"""
        SELECT
          COUNT(*)::BIGINT AS rows_long,
          COUNT(DISTINCT timestamp)::BIGINT AS rows_wide,
          COUNT(DISTINCT {equip_expr})::BIGINT AS equips,
          COUNT(DISTINCT {var_expr})::BIGINT AS vars,
          MIN(timestamp) AS min_ts,
          MAX(timestamp) AS max_ts
        FROM medicoes
        WHERE {where_sql};
        """,
        tuple(where_params),
    ).fetchone()

    rows_long = int(row[0] or 0)
    rows_wide = int(row[1] or 0)
    equips = int(row[2] or 0)
    vars_ = int(row[3] or 0)
    min_ts = row[4]
    max_ts = row[5]
    span_days = 0.0
    if min_ts is not None and max_ts is not None:
        span_days = max((max_ts - min_ts).total_seconds() / 86400.0, 0.0)
    estimated_series = int(equips * vars_)
    filesize_mb = _estimate_filesize_mb(intent, rows_long, rows_wide, estimated_series)
    return {
        "estimated_rows_long": rows_long,
        "estimated_rows_wide": rows_wide,
        "estimated_series": estimated_series,
        "estimated_equips": equips,
        "estimated_vars": vars_,
        "min_ts": min_ts,
        "max_ts": max_ts,
        "time_span_days": span_days,
        "estimated_filesize_mb": filesize_mb,
    }


def run_audit(
    *,
    metrics: Dict[str, Any],
    intent: ExportIntent,
) -> List[AuditFinding]:
    findings: List[AuditFinding] = []
    rows_long = int(metrics.get("estimated_rows_long", 0))
    rows_wide = int(metrics.get("estimated_rows_wide", 0))
    series = int(metrics.get("estimated_series", 0))
    span_days = float(metrics.get("time_span_days", 0.0))
    min_ts = metrics.get("min_ts")
    max_ts = metrics.get("max_ts")
    filesize_mb = float(metrics.get("estimated_filesize_mb", 0.0))

    recs = _build_recommendations(min_ts=min_ts, max_ts=max_ts, intent=intent)

    if intent.format == "xlsx_dashboard" and rows_wide > EXCEL_MAX_ROWS:
        findings.append(
            AuditFinding(
                code="XLSX_EXCEL_ROWS_HARD_STOP",
                severity="ERROR",
                title="XLSX excede limite fisico do Excel",
                details=f"Timestamps estimados: {rows_wide:,} > limite {EXCEL_MAX_ROWS:,}.",
                recommended_actions=recs,
                hard_stop=True,
            )
        )
    elif rows_wide >= int(EXCEL_MAX_ROWS * EXCEL_SAFE_HEADROOM):
        findings.append(
            AuditFinding(
                code="EXCEL_ROWS_NEAR_LIMIT",
                severity="WARN",
                title="Exportacao proxima do limite do Excel",
                details=f"Timestamps estimados: {rows_wide:,} (>= {int(EXCEL_MAX_ROWS * EXCEL_SAFE_HEADROOM):,}).",
                recommended_actions=recs,
            )
        )

    if intent.destination_excel and intent.format in {"csv_long", "csv_wide"} and rows_wide > EXCEL_MAX_ROWS:
        findings.append(
            AuditFinding(
                code="CSV_FOR_EXCEL_ROWS_OVER_LIMIT",
                severity="ERROR",
                title="CSV nao cabera no Excel com esse recorte",
                details=f"Timestamps estimados: {rows_wide:,} > {EXCEL_MAX_ROWS:,}.",
                recommended_actions=recs,
                hard_stop=False,
            )
        )

    if rows_long >= PERFORMANCE_WARN_ROWS:
        findings.append(
            AuditFinding(
                code="PERFORMANCE_HIGH_VOLUME",
                severity="WARN",
                title="Volume alto para exportacao",
                details=f"Linhas LONG estimadas: {rows_long:,}. Pode haver lentidao.",
                recommended_actions=recs,
            )
        )

    if filesize_mb >= FILESIZE_WARN_MB:
        findings.append(
            AuditFinding(
                code="FILESIZE_HEAVY",
                severity="WARN",
                title="Arquivo estimado pesado",
                details=f"Tamanho estimado: {filesize_mb:.1f} MB.",
                recommended_actions=recs,
            )
        )

    findings.append(
        AuditFinding(
            code="AUDIT_SUMMARY",
            severity="INFO",
            title="Resumo de auditoria",
            details=(
                f"rows_long={rows_long:,}, rows_wide={rows_wide:,}, "
                f"series={series:,}, span={span_days:.1f} dias."
            ),
            recommended_actions=recs,
        )
    )
    return findings


def apply_recommendation(state: Dict[str, Any], action_id: str) -> Dict[str, Any]:
    out = dict(state)
    now = dt.datetime.now().replace(microsecond=0)
    if action_id.startswith("set_last_") and action_id.endswith("d"):
        days = int(action_id.replace("set_last_", "").replace("d", ""))
        out["t0"] = (now - dt.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        out["t1"] = now.strftime("%Y-%m-%d %H:%M:%S")
    elif action_id.startswith("set_timefloor_"):
        out["time_floor"] = action_id.replace("set_timefloor_", "").upper()
    elif action_id == "set_agg_last":
        out["agg"] = "last"
    elif action_id == "set_max_ts_safe":
        out["max_timestamps"] = XLSX_MAX_TIMESTAMPS_DEFAULT
    elif action_id == "reduce_selection_hint":
        out["selection_hint"] = True
    return out
