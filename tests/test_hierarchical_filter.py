from __future__ import annotations

from db.query_builder import build_distinct_query, build_filters
from xlsx_selection import pontos_to_xlsx_selection


def test_cascading_distinct_query_uses_upstream_filters() -> None:
    sql, params = build_distinct_query(
        target_col="EQUIPAMENTO",
        ano=2025,
        mes=1,
        se_sel=["VIA1"],
        bay_sel=["AL15"],
        ponto_id_like="TR-1",
        limit=500,
    )
    assert "SELECT DISTINCT CAST(EQUIPAMENTO AS VARCHAR) AS v" in sql
    assert "SE IN (?)" in sql
    assert "BAY IN (?)" in sql
    assert "LOWER(CAST(ponto_id AS VARCHAR)) LIKE '%' || ? || '%'" in sql
    assert "LIMIT ?" in sql
    assert params[-1] == 500


def test_build_filters_scopes_by_selected_points_and_vars() -> None:
    sql, params = build_filters(
        equips_selected=[],
        equip_like=None,
        vars_sel=["IA", "IB"],
        ponto_ids_sel=["SE1|B1|TR-1|Terminal1", "SE1|B1|TR-1|Terminal2"],
        ano=2025,
        mes=1,
        t0="2025-01-01 00:00:00",
        t1="2025-01-31 23:59:59",
    )
    assert "var IN (?,?)" in sql
    assert "CAST(ponto_id AS VARCHAR) IN (?,?)" in sql
    assert "?" in sql
    assert "TR-1|Terminal1" not in sql
    assert any("TR-1|Terminal1" in str(p) for p in params)


def test_injection_is_parameterized_for_ponto_id_search() -> None:
    attack = "TR-1' OR 1=1 --"
    sql, params = build_filters(
        equips_selected=[],
        equip_like=None,
        vars_sel=[],
        ponto_id_like=attack,
        ano=2025,
        mes=1,
        t0=None,
        t1=None,
    )
    assert "OR 1=1" not in sql
    assert attack not in sql
    assert "?" in sql
    assert any("1=1" in str(p) for p in params)


def test_pontos_to_xlsx_selection_merges_multiple_terminals() -> None:
    out = pontos_to_xlsx_selection(
        ["SE1|B1|TR-1|Terminal1", "SE1|B1|TR-1|Terminal2", "SE1|AL15|52-6|Terminal1"],
        ["IA", "IB", "IA"],
    )
    assert out == {"52-6": ["IA", "IB"], "TR-1": ["IA", "IB"]}


def test_pontos_to_xlsx_selection_ignores_malformed_points() -> None:
    out = pontos_to_xlsx_selection(
        ["SE1|B1|TR-1|Terminal1", "invalid", "SE2|B2||Terminal2"],
        ["P"],
    )
    assert out == {"TR-1": ["P"]}
