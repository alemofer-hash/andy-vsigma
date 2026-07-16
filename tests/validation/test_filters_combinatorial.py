from __future__ import annotations

import itertools
from typing import List, Tuple

import pytest

import andys_table_app as app
from db.query_builder import build_distinct_query, build_filters, build_ponto_query, build_vars_for_pontos_query


 # --- NEW: powerset local para enumeracao exaustiva de multiselect ---
def _powerset(values, include_empty: bool = True):
    out = []
    start = 0 if include_empty else 1
    for r in range(start, len(values) + 1):
        out.extend(tuple(c) for c in itertools.combinations(values, r))
    return out


@pytest.mark.validation
@pytest.mark.combinatorial
@pytest.mark.integration
def test_filter_and_point_resolution_cartesian_domain(validation_domain, run_sql) -> None:
    # --- NEW: executa matriz cartesiana de filtros e valida pontos/variaveis ---
    periods = validation_domain["periods"]
    se_sets = _powerset(validation_domain["se"], include_empty=True)
    bay_sets = _powerset(validation_domain["bay"], include_empty=True)
    equip_sets = _powerset(validation_domain["equip"], include_empty=True)
    terminal_sets = _powerset(validation_domain["terminal"], include_empty=True)
    var_domain = set(validation_domain["vars_standard"] + validation_domain["vars_custom"])

    seen_zero = 0
    seen_one = 0
    seen_many = 0
    executed = 0

    for (ano, mes), se_sel, bay_sel, equip_sel, terminal_sel in itertools.product(
        periods, se_sets, bay_sets, equip_sets, terminal_sets
    ):
        sql_p, p_p = build_ponto_query(
            ano=ano,
            mes=mes,
            se_sel=list(se_sel),
            bay_sel=list(bay_sel),
            equipamento_sel=list(equip_sel),
            terminal_sel=list(terminal_sel),
            limit=500,
        )
        pontos = [str(r[0]) for r in run_sql(sql_p, p_p) if r[0] is not None]
        executed += 1
        if len(pontos) == 0:
            seen_zero += 1
            continue
        if len(pontos) == 1:
            seen_one += 1
        else:
            seen_many += 1

        sql_v, p_v = build_vars_for_pontos_query(ano=ano, mes=mes, ponto_ids_sel=pontos)
        vars_found = {str(r[0]) for r in run_sql(sql_v, p_v)}
        assert vars_found
        assert vars_found.issubset(var_domain)

    assert executed > 0
    assert seen_zero > 0
    assert seen_one > 0
    assert seen_many > 0


@pytest.mark.validation
@pytest.mark.combinatorial
def test_query_builder_clause_presence_exhaustive() -> None:
    # --- NEW: varre 2^8 combinacoes de clausulas e verifica seguranca ---
    # flags: se,bay,equip,terminal,vars,pontos,ponto_like,equip_like
    for flags in itertools.product([False, True], repeat=8):
        use_se, use_bay, use_equip, use_terminal, use_vars, use_points, use_p_like, use_e_like = flags
        se_vals = ["SE1", "SE2"] if use_se else []
        bay_vals = ["BAY_A", "BAY_B"] if use_bay else []
        equip_vals = ["TR-1", "AL-1"] if use_equip else []
        terminal_vals = ["Terminal1", "Terminal2"] if use_terminal else []
        vars_vals = ["IA", "CUSTOM_X"] if use_vars else []
        points_vals = ["SE1|BAY_A|TR-1|Terminal1", "SE1|BAY_B|TR-1|Terminal2"] if use_points else []
        p_like = "TR-1' OR 1=1 --" if use_p_like else None
        e_like = "TR-1' OR 1=1 --" if use_e_like else None

        where_sql, params = build_filters(
            equips_selected=[],
            equip_like=e_like,
            vars_sel=vars_vals,
            se_sel=se_vals,
            bay_sel=bay_vals,
            equipamento_sel=equip_vals,
            terminal_sel=terminal_vals,
            ponto_ids_sel=points_vals,
            ponto_id_like=p_like,
            ano=2025,
            mes=1,
            t0=None,
            t1=None,
        )
        assert "?" in where_sql
        assert "OR 1=1" not in where_sql
        assert "TR-1' OR 1=1 --" not in where_sql
        assert isinstance(params, tuple)


@pytest.mark.validation
@pytest.mark.combinatorial
def test_autofill_and_pruning_exhaustive(monkeypatch: pytest.MonkeyPatch) -> None:
    # --- NEW: valida pruning + autofill em todos estados discretos relevantes ---
    option_states: List[List[str]] = [[], ["A"], ["A", "B"]]
    current_states: List[List[str]] = [[], ["A"], ["B"], ["A", "B"]]

    for valid_options, current in itertools.product(option_states, current_states):
        state = {"k": list(current)}
        monkeypatch.setattr(app.st, "session_state", state)
        app._prune_state("k", valid_options)
        pruned = list(app.st.session_state["k"])
        assert all(v in valid_options for v in pruned)

        changed = app._autofill_single_option("k", valid_options)
        if len(valid_options) == 1:
            assert app.st.session_state["k"] == [valid_options[0]]
            assert changed in {True, False}
        else:
            assert app.st.session_state["k"] == pruned
            assert changed is False


@pytest.mark.validation
@pytest.mark.combinatorial
@pytest.mark.integration
def test_distinct_query_cascade_levels(validation_domain, run_sql) -> None:
    # --- NEW: checa encadeamento SE->BAY->EQUIPAMENTO->TERMINAL ---
    ano, mes = validation_domain["periods"][0]
    sql_se, p_se = build_distinct_query(target_col="SE", ano=ano, mes=mes)
    se = [str(r[0]) for r in run_sql(sql_se, p_se)]
    assert se

    sql_bay, p_bay = build_distinct_query(target_col="BAY", ano=ano, mes=mes, se_sel=[se[0]], include_empty=True)
    bay = [str(r[0]) for r in run_sql(sql_bay, p_bay)]
    assert bay

    sql_eq, p_eq = build_distinct_query(target_col="EQUIPAMENTO", ano=ano, mes=mes, se_sel=[se[0]], bay_sel=[bay[0]], include_empty=True)
    eq = [str(r[0]) for r in run_sql(sql_eq, p_eq)]
    assert eq

    sql_t, p_t = build_distinct_query(
        target_col="TERMINAL",
        ano=ano,
        mes=mes,
        se_sel=[se[0]],
        bay_sel=[bay[0]],
        equipamento_sel=[eq[0]],
        include_empty=True,
    )
    terminal = [str(r[0]) for r in run_sql(sql_t, p_t)]
    assert terminal
