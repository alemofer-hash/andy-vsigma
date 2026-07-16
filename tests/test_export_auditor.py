from __future__ import annotations

import datetime as dt
from pathlib import Path

import duckdb

from audit import export_auditor
from audit.export_auditor import ExportIntent, estimate_export_shape, run_audit
from config import EXCEL_MAX_ROWS


def _mk_db(path: Path) -> str:
    con = duckdb.connect(str(path))
    try:
        con.execute(
            """
            CREATE TABLE medicoes (
              timestamp TIMESTAMP,
              equip_id VARCHAR,
              var VARCHAR,
              valor DOUBLE
            );
            """
        )
        con.execute(
            """
            INSERT INTO medicoes VALUES
            ('2025-01-01 00:00:00', 'EQ1', 'IA', 10.0),
            ('2025-01-01 00:15:00', 'EQ1', 'IA', 11.0),
            ('2025-01-01 00:15:00', 'EQ2', 'IB', 12.0);
            """
        )
    finally:
        con.close()
    return str(path)


def test_run_audit_returns_error_when_timestamps_exceed_excel_limit_with_mock(monkeypatch) -> None:
    def fake_estimate(**_: object):
        return {
            "estimated_rows_long": EXCEL_MAX_ROWS * 3,
            "estimated_rows_wide": EXCEL_MAX_ROWS + 10,
            "estimated_series": 200,
            "min_ts": dt.datetime(2020, 1, 1),
            "max_ts": dt.datetime(2026, 1, 1),
            "time_span_days": 365 * 6,
            "estimated_filesize_mb": 900.0,
        }

    monkeypatch.setattr(export_auditor, "estimate_export_shape", fake_estimate)
    intent = ExportIntent(format="xlsx_dashboard")
    metrics = export_auditor.estimate_export_shape(con=None, where_sql="TRUE", where_params=tuple(), intent=intent)  # type: ignore[arg-type]
    findings = run_audit(metrics=metrics, intent=intent)
    assert any(f.severity == "ERROR" for f in findings)
    assert any(f.hard_stop for f in findings)


def test_run_audit_warns_when_near_limit(tmp_path: Path) -> None:
    db = _mk_db(tmp_path / "a.duckdb")
    con = duckdb.connect(db, read_only=True)
    try:
        intent = ExportIntent(format="csv_wide", destination_excel=True)
        metrics = {
            "estimated_rows_long": 1000,
            "estimated_rows_wide": int(EXCEL_MAX_ROWS * 0.95),
            "estimated_series": 20,
            "min_ts": dt.datetime(2024, 1, 1),
            "max_ts": dt.datetime(2025, 1, 1),
            "time_span_days": 366.0,
            "estimated_filesize_mb": 80.0,
        }
        findings = run_audit(metrics=metrics, intent=intent)
    finally:
        con.close()
    assert any(f.severity == "WARN" for f in findings)


def test_recommendations_coherent_with_span_and_series(tmp_path: Path) -> None:
    db = _mk_db(tmp_path / "b.duckdb")
    con = duckdb.connect(db, read_only=True)
    try:
        intent = ExportIntent(format="xlsx_dashboard")
        metrics = estimate_export_shape(
            con=con,
            where_sql="TRUE",
            where_params=tuple(),
            intent=intent,
        )
        findings = run_audit(metrics=metrics, intent=intent)
    finally:
        con.close()
    all_actions = {a.id for f in findings for a in f.recommended_actions}
    assert "set_last_30d" in all_actions
    assert "set_agg_last" in all_actions
    assert "set_max_ts_safe" in all_actions
