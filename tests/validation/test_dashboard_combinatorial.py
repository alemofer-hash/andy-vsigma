from __future__ import annotations

import itertools
import uuid
from pathlib import Path
from typing import Dict

import duckdb
import openpyxl
import pandas as pd
import pytest

from andys_report_runner import aggregate_long, construir_bi_excel_multi_equip_multi_var_long


# --- NEW: base long focada nos cenarios de dashboard ---
def _load_base_df(db_path: str) -> pd.DataFrame:
    con = duckdb.connect(db_path, read_only=True)
    try:
        df = con.execute(
            """
            SELECT timestamp, SE, BAY, TERMINAL, equip_id, var, classe, valor
            FROM medicoes
            WHERE equip_id = 'TR-1'
            ORDER BY timestamp ASC
            """
        ).df()
    finally:
        con.close()
    if "TIMESTAMP" in df.columns and "timestamp" not in df.columns:
        df = df.rename(columns={"TIMESTAMP": "timestamp"})
    return df


@pytest.mark.validation
@pytest.mark.combinatorial
@pytest.mark.integration
@pytest.mark.dashboard
def test_dashboard_cartesian_combinations(canonical_validation_workspace: Dict[str, Path]) -> None:
    # --- NEW: valida 2x2x2 combinacoes de serie e estrutura de grafico ---
    db_path = str(canonical_validation_workspace["db_path"])
    out_dir = canonical_validation_workspace["exports"] / "combinatorial_dashboard"
    out_dir.mkdir(parents=True, exist_ok=True)

    base_df = _load_base_df(db_path)
    assert not base_df.empty

    bay_domains = [["BAY_A"], ["BAY_A", "BAY_B"]]
    terminal_domains = [["Terminal1"], ["Terminal1", "Terminal2"]]
    var_domains = [["IA"], ["IA", "IB"]]

    executed = 0
    for bays, terms, vars_sel in itertools.product(bay_domains, terminal_domains, var_domains):
        df_case = base_df[
            base_df["BAY"].astype(str).isin(bays)
            & base_df["TERMINAL"].astype(str).isin(terms)
            & base_df["var"].astype(str).isin(vars_sel)
        ].copy()
        if df_case.empty:
            continue

        df_agg = aggregate_long(df_case, agg="max", time_floor=None)
        expected_series = int(df_agg["_KEY"].nunique())
        assert expected_series > 0

        out_path = out_dir / f"dash_{len(bays)}_{len(terms)}_{len(vars_sel)}_{uuid.uuid4().hex[:6]}.xlsx"
        out_file, _warnings = construir_bi_excel_multi_equip_multi_var_long(
            long_df=df_agg,
            xlsx_out=str(out_path),
            report_meta={"combo": f"{bays}|{terms}|{vars_sel}"},
            selected_pairs=[("TR-1", v) for v in vars_sel],
        )
        assert Path(out_file).exists()

        wb = openpyxl.load_workbook(out_file, data_only=False)
        try:
            ws_view = wb["VIEW_MX"]
            ws_dash = wb["DASHBOARD"]
            assert ws_view["A4"].value == "TIMESTAMP_TEXT"
            assert isinstance(ws_view["A8"].value, str)
            assert ws_dash._charts, "Esperado grafico no DASHBOARD."
            chart = ws_dash._charts[0]
            assert len(chart.series) == expected_series
        finally:
            wb.close()
        executed += 1

    assert executed == 8
