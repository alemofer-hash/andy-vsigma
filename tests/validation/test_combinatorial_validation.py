from __future__ import annotations

from typing import Dict, List

import duckdb
import pytest

import andys_table_app as app
from db.query_builder import build_filters, build_pagination
from xlsx_selection import pontos_to_xlsx_selection


@pytest.mark.validation
@pytest.mark.combinatorial
def test_canonical_domain_matrix_size(validation_domain) -> None:
    # --- NEW: explicita tamanho da matriz canonica e evita reducao silenciosa ---
    periods = validation_domain["periods"]
    se_n = 2 ** len(validation_domain["se"])
    bay_n = 2 ** len(validation_domain["bay"])
    equip_n = 2 ** len(validation_domain["equip"])
    term_n = 2 ** len(validation_domain["terminal"])
    total = len(periods) * se_n * bay_n * equip_n * term_n
    # Matriz principal de filtros: dominio finito explicito.
    assert total == 768


@pytest.mark.validation
@pytest.mark.combinatorial
@pytest.mark.integration
def test_query_page_combinations_empty_single_multi_page(canonical_validation_workspace: Dict[str, str]) -> None:
    # --- NEW: valida query_page em cenarios vazio, pagina unica e multipagina ---
    db_path = str(canonical_validation_workspace["db_path"])
    con = duckdb.connect(db_path, read_only=True)
    try:
        ano, mes = con.execute(
            """
            SELECT ano, mes
            FROM medicoes
            WHERE var = 'IA'
            ORDER BY ano DESC, mes DESC
            LIMIT 1
            """
        ).fetchone()
        points = [
            str(r[0])
            for r in con.execute(
                "SELECT DISTINCT ponto_id FROM medicoes WHERE ano = ? AND mes = ? ORDER BY ponto_id LIMIT 3;",
                [int(ano), int(mes)],
            ).fetchall()
        ]
    finally:
        con.close()

    # caso 1: vazio
    where_sql, params = build_filters(
        equips_selected=[],
        equip_like=None,
        vars_sel=["VAR_INEXISTENTE"],
        ponto_ids_sel=points,
        ano=int(ano),
        mes=int(mes),
        t0=None,
        t1=None,
    )
    pg_sql, pg_params = build_pagination(limit=50, offset=0)
    total, df = app.query_page(db_path, where_sql, params, pg_sql, pg_params, "ORDER BY timestamp ASC")
    assert total == 0
    assert df.empty

    # caso 2: uma pagina
    where_sql2, params2 = build_filters(
        equips_selected=[],
        equip_like=None,
        vars_sel=["IA"],
        ponto_ids_sel=points,
        ano=int(ano),
        mes=int(mes),
        t0=None,
        t1=None,
    )
    pg_sql2, pg_params2 = build_pagination(limit=1000, offset=0)
    total2, df2 = app.query_page(db_path, where_sql2, params2, pg_sql2, pg_params2, "ORDER BY timestamp ASC")
    assert total2 >= len(df2) >= 1

    # caso 3: multipagina
    pg_sql3, pg_params3 = build_pagination(limit=1, offset=0)
    total3, df3 = app.query_page(db_path, where_sql2, params2, pg_sql3, pg_params3, "ORDER BY timestamp DESC")
    assert total3 >= 1
    assert len(df3) == 1
    if total3 > 1:
        pg_sql4, pg_params4 = build_pagination(limit=1, offset=1)
        total4, df4 = app.query_page(db_path, where_sql2, params2, pg_sql4, pg_params4, "ORDER BY timestamp DESC")
        assert total4 == total3
        assert len(df4) == 1


@pytest.mark.validation
@pytest.mark.combinatorial
@pytest.mark.integration
def test_xlsx_selection_mapping_combinations(canonical_validation_workspace: Dict[str, str]) -> None:
    # --- NEW: valida combinacoes de pontos->equipamento e deduplicacao de variaveis ---
    db_path = str(canonical_validation_workspace["db_path"])
    con = duckdb.connect(db_path, read_only=True)
    try:
        points_tr = [str(r[0]) for r in con.execute("SELECT DISTINCT ponto_id FROM medicoes WHERE EQUIPAMENTO = 'TR-1' ORDER BY ponto_id LIMIT 2;").fetchall()]
        points_al = [str(r[0]) for r in con.execute("SELECT DISTINCT ponto_id FROM medicoes WHERE EQUIPAMENTO = 'AL-1' ORDER BY ponto_id LIMIT 1;").fetchall()]
    finally:
        con.close()

    assert len(points_tr) == 2
    assert len(points_al) == 1

    point_sets = [
        [points_tr[0]],
        [points_tr[0], points_tr[1]],  # mesmo equipamento, terminais distintos
        [points_tr[0], points_al[0]],  # equipamentos distintos
    ]
    var_sets = [["IA"], ["IA", "IB"], ["IA", "IB", "IA"]]

    for pts in point_sets:
        for vars_sel in var_sets:
            out = pontos_to_xlsx_selection(pts, vars_sel)
            assert out
            for equip, vars_out in out.items():
                assert isinstance(equip, str) and equip
                assert vars_out == sorted(set(vars_sel), key=vars_sel.index)


@pytest.mark.validation
@pytest.mark.combinatorial
@pytest.mark.integration
def test_internal_point_filter_exactness(canonical_validation_workspace: Dict[str, str]) -> None:
    # --- NEW: garante que filtro final respeita ponto_id exato internamente ---
    db_path = str(canonical_validation_workspace["db_path"])
    con = duckdb.connect(db_path, read_only=True)
    try:
        ano, mes = con.execute(
            """
            SELECT ano, mes
            FROM medicoes
            WHERE var = 'IA'
            ORDER BY ano DESC, mes DESC
            LIMIT 1
            """
        ).fetchone()
        points = [
            str(r[0])
            for r in con.execute(
                "SELECT DISTINCT ponto_id FROM medicoes WHERE ano = ? AND mes = ? ORDER BY ponto_id LIMIT 2;",
                [int(ano), int(mes)],
            ).fetchall()
        ]
    finally:
        con.close()

    where_sql, params = build_filters(
        equips_selected=[],
        equip_like=None,
        vars_sel=["IA", "IB"],
        ponto_ids_sel=points,
        ano=int(ano),
        mes=int(mes),
        t0=None,
        t1=None,
    )
    pg_sql, pg_params = build_pagination(limit=500, offset=0)
    _total, df = app.query_page(db_path, where_sql, params, pg_sql, pg_params, "ORDER BY timestamp ASC")
    assert not df.empty
    assert set(df["ponto_id"].astype(str).unique()).issubset(set(points))
