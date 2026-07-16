from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import andys_table_app as app
from andys_indexer import get_variable_cols
from db.query_builder import build_distinct_query, build_filters, build_ponto_query, build_vars_for_pontos_query
from xlsx_selection import pontos_to_xlsx_selection


def test_require_connection_shows_error_and_stops(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, int] = {"error": 0, "sidebar_error": 0, "stop": 0}

    class _Sidebar:
        def error(self, *_args, **_kwargs):
            calls["sidebar_error"] += 1

        def success(self, *_args, **_kwargs):
            return None

    def _stop():
        calls["stop"] += 1
        raise RuntimeError("stopped")

    monkeypatch.setattr(app, "get_con", lambda _db_path: None)
    monkeypatch.setattr(app.st, "sidebar", _Sidebar())
    monkeypatch.setattr(app.st, "error", lambda *_a, **_k: calls.__setitem__("error", calls["error"] + 1))
    monkeypatch.setattr(app.st, "stop", _stop)

    with pytest.raises(RuntimeError, match="stopped"):
        app.require_connection("fake.duckdb")

    assert calls["sidebar_error"] == 1
    assert calls["error"] == 1
    assert calls["stop"] == 1


def test_get_variable_cols_keeps_custom_measurements() -> None:
    df = pd.DataFrame(
        {
            "TIMESTAMP": ["2025-01-01 00:00:00"],
            "SE": ["X"],
            "BAY": ["Y"],
            "EQUIPAMENTO": ["EQ1"],
            "TERMINAL": ["1"],
            "IA": ["1,0"],
            "IB": ["2,0"],
            "IC": ["3,0"],
            "VAB": ["13,8"],
            "CUSTOM_VAR": ["42,1"],
        }
    )
    cols = get_variable_cols(df)
    assert "IA" in cols
    assert "IB" in cols
    assert "IC" in cols
    assert "VAB" in cols
    assert "CUSTOM_VAR" in cols
    assert "SE" not in cols


def test_cascading_helpers_parameterize_values() -> None:
    sql, params = build_distinct_query(
        target_col="TERMINAL",
        ano=2026,
        mes=3,
        se_sel=["SAUX"],
        bay_sel=["AL5"],
        equipamento_sel=["TR-1"],
    )
    assert "?" in sql
    assert "SAUX" not in sql
    assert "AL5" not in sql
    assert "TR-1" not in sql
    assert params[:5] == (2026, 3, "SAUX", "AL5", "TR-1")


def test_pontos_to_xlsx_selection_collapses_terminals_and_dedups() -> None:
    out = pontos_to_xlsx_selection(
        ["SE1|B1|TR-1|Terminal1", "SE1|B1|TR-1|Terminal2", "bad", "SE1|AL5|52-6|Terminal1"],
        ["IA", "IB", "IA"],
    )
    assert out == {"52-6": ["IA", "IB"], "TR-1": ["IA", "IB"]}


def test_year_month_filter_uses_bind_params() -> None:
    sql, params = build_filters(
        equips_selected=[],
        equip_like=None,
        vars_sel=[],
        ano=2026,
        mes=3,
        t0=None,
        t1=None,
    )
    assert "ano = ?" in sql
    assert "mes = ?" in sql
    assert params[:2] == (2026, 3)


def test_vars_query_scoped_to_ponto_ids() -> None:
    sql, params = build_vars_for_pontos_query(
        ano=2026,
        mes=3,
        ponto_ids_sel=["SE1|B1|TR-1|Terminal1", "SE1|B1|TR-1|Terminal2"],
    )
    assert "SELECT DISTINCT var" in sql
    assert "CAST(ponto_id AS VARCHAR) IN (?,?)" in sql
    assert params[:2] == (2026, 3)
    assert params[2:] == ("SE1|B1|TR-1|Terminal1", "SE1|B1|TR-1|Terminal2")


def test_ponto_candidates_query_contains_limit_and_params() -> None:
    sql, params = build_ponto_query(
        ano=2026,
        mes=3,
        se_sel=["SAUX"],
        bay_sel=["AL5"],
        equipamento_sel=["TR-1"],
        terminal_sel=["Terminal1"],
        ponto_id_like="TR-1",
        limit=300,
    )
    assert "SELECT DISTINCT CAST(ponto_id AS VARCHAR) AS v" in sql
    assert "LIMIT ?" in sql
    assert params[-1] == 300


def test_autofill_single_option_sets_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app.st, "session_state", {"filter_bay": []})
    changed = app._autofill_single_option("filter_bay", ["BAY_A"])
    assert changed is True
    assert app.st.session_state["filter_bay"] == ["BAY_A"]


def test_resolve_effective_points_uses_all_candidates() -> None:
    out = app._resolve_effective_points(["P1", "P2"])
    assert out == ["P1", "P2"]


def test_ui_no_longer_exposes_ponto_multiselect_label() -> None:
    src = Path("andys_table_app.py").read_text(encoding="utf-8")
    assert "Pontos (ponto_id)" not in src


def test_points_are_resolved_in_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        app,
        "load_ponto_options",
        lambda *_a, **_k: ["SE1|B1|EQ1|Terminal1", "SE1|B2|EQ1|Terminal1"],
    )
    out = app._resolve_points_backend(
        "fake.duckdb",
        ano=2026,
        mes=3,
        se_sel=("SE1",),
        bay_sel=("B1", "B2"),
        equipamento_sel=("EQ1",),
        terminal_sel=("Terminal1",),
        ponto_id_like="EQ1",
        limit=500,
    )
    assert out == ["SE1|B1|EQ1|Terminal1", "SE1|B2|EQ1|Terminal1"]


def test_query_page_raises_clear_error_when_count_row_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeCur:
        def execute(self, _sql, _params=None):
            return self

        def fetchone(self):
            return None

        def df(self):
            return pd.DataFrame()

    monkeypatch.setattr(app, "get_cur", lambda _db_path: _FakeCur())
    monkeypatch.setattr(app, "_projected_base_select", lambda _db_path: "timestamp, equip_id, var, classe, valor, ano, mes")

    with pytest.raises(RuntimeError, match="COUNT\\(\\*\\) retornou vazio"):
        app.query_page(
            "fake.duckdb",
            where_sql="TRUE",
            where_params=(),
            pagination_sql="LIMIT ? OFFSET ?",
            pagination_params=(10, 0),
            order_sql="ORDER BY timestamp ASC",
        )
