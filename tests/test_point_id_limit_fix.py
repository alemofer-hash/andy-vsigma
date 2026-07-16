from __future__ import annotations

from pathlib import Path
from typing import List
import uuid

import duckdb
import pandas as pd
import pytest

import andys_table_app as app
from db.query_builder import build_ponto_query, build_vars_for_context_query, build_filters, build_pagination


def _clear_streamlit_caches() -> None:
    for fn_name in ("get_con", "load_vars_by_pontos", "load_vars_by_context"):
        fn = getattr(app, fn_name, None)
        clear = getattr(fn, "clear", None)
        if callable(clear):
            clear()


def _make_medicoes_db(db_path: Path, n_points: int = 450) -> None:
    con = duckdb.connect(str(db_path))
    con.execute(
        """
        CREATE TABLE medicoes (
          timestamp TIMESTAMP,
          ano INTEGER,
          mes INTEGER,
          SE VARCHAR,
          BAY VARCHAR,
          EQUIPAMENTO VARCHAR,
          TERMINAL VARCHAR,
          ponto_id VARCHAR,
          equip_id VARCHAR,
          var VARCHAR,
          classe VARCHAR,
          valor DOUBLE
        );
        """
    )
    rows: List[tuple] = []
    vars_ = ["P", "Q", "IA", "IB", "IC"]
    for i in range(n_points):
        point = f"SE1|BAY_A|TR-1|Terminal1|{i}"
        for v in vars_:
            rows.append(
                (
                    "2025-01-01 00:00:00",
                    2025,
                    1,
                    "SE1",
                    "BAY_A",
                    "TR-1",
                    "Terminal1",
                    point,
                    "TR-1",
                    v,
                    "MED",
                    float(i % 10),
                )
            )
    con.executemany(
        """
        INSERT INTO medicoes
        (timestamp, ano, mes, SE, BAY, EQUIPAMENTO, TERMINAL, ponto_id, equip_id, var, classe, valor)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    con.close()


def test_load_vars_by_pontos_deduplicates_before_query_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_streamlit_caches()
    captured: dict = {"points": None}

    class _FakeCur:
        def execute(self, _sql, _params=None):
            return self

        def fetchall(self):
            return [("IA",), ("IB",)]

    def _fake_builder(*, ano, mes, ponto_ids_sel):
        captured["points"] = list(ponto_ids_sel)
        return "SELECT 'IA' as var UNION ALL SELECT 'IB' as var", ()

    monkeypatch.setattr(app, "get_cur", lambda _db: _FakeCur())
    monkeypatch.setattr(app, "build_vars_for_pontos_query", _fake_builder)

    out = app.load_vars_by_pontos(
        "fake.duckdb",
        tuple(["SE1|BAY_A|TR-1|Terminal1"] * 1000),
        ano=2025,
        mes=1,
        t0=None,
        t1=None,
    )
    assert out == ["IA", "IB"]
    assert captured["points"] == ["SE1|BAY_A|TR-1|Terminal1"]


def test_build_vars_for_context_query_keeps_bind_safety() -> None:
    sql, params = build_vars_for_context_query(
        ano=2025,
        mes=1,
        se_sel=["SE1"],
        bay_sel=["BAY_A"],
        equipamento_sel=["TR-1"],
        terminal_sel=["Terminal1"],
        ponto_id_like="TR-1' OR 1=1 --",
    )
    assert "SELECT DISTINCT var" in sql
    assert "?" in sql
    assert "OR 1=1" not in sql
    assert "TR-1' OR 1=1 --" not in sql
    assert "se1" in [str(p).lower() for p in params]


def test_large_feeder_variable_discovery_without_point_list_overflow() -> None:
    _clear_streamlit_caches()
    base = (Path.cwd() / ".validation_tmp" / "tests_fix" / f"vars_ctx_{uuid.uuid4().hex[:8]}").resolve()
    base.mkdir(parents=True, exist_ok=True)
    db_path = base / "medicoes_large.duckdb"
    _make_medicoes_db(db_path, n_points=450)

    vars_found = app.load_vars_by_context(
        str(db_path),
        ano=2025,
        mes=1,
        se_sel=("SE1",),
        bay_sel=("BAY_A",),
        equipamento_sel=("TR-1",),
        terminal_sel=("Terminal1",),
        ponto_id_like="",
    )
    assert {"P", "Q", "IA", "IB", "IC"}.issubset(set(vars_found))


def test_internal_point_resolution_remains_exact_for_query_path() -> None:
    _clear_streamlit_caches()
    base = (Path.cwd() / ".validation_tmp" / "tests_fix" / f"vars_exact_{uuid.uuid4().hex[:8]}").resolve()
    base.mkdir(parents=True, exist_ok=True)
    db_path = base / "medicoes_exact.duckdb"
    _make_medicoes_db(db_path, n_points=20)

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        sql_p, params_p = build_ponto_query(
            ano=2025,
            mes=1,
            se_sel=["SE1"],
            bay_sel=["BAY_A"],
            equipamento_sel=["TR-1"],
            terminal_sel=["Terminal1"],
            ponto_id_like="",
            limit=500,
        )
        resolved_points = {str(r[0]) for r in con.execute(sql_p, params_p).fetchall()}
    finally:
        con.close()

    where_sql, where_params = build_filters(
        equips_selected=[],
        equip_like=None,
        vars_sel=["IA"],
        se_sel=["SE1"],
        bay_sel=["BAY_A"],
        equipamento_sel=["TR-1"],
        terminal_sel=["Terminal1"],
        ponto_ids_sel=None,
        ano=2025,
        mes=1,
        t0=None,
        t1=None,
    )
    pg_sql, pg_params = build_pagination(limit=500, offset=0)
    _total, df = app.query_page(
        str(db_path),
        where_sql,
        where_params,
        pg_sql,
        pg_params,
        "ORDER BY timestamp ASC",
    )
    assert not df.empty
    assert set(df["ponto_id"].astype(str).unique()).issubset(resolved_points)
