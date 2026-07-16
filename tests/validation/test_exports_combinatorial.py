from __future__ import annotations

import itertools
import uuid
from pathlib import Path
from typing import Dict, List

import duckdb
import pandas as pd
import pytest

from andys_report_runner import aggregate_long, construir_bi_excel_multi_equip_multi_var_long


# --- NEW: carrega base long para cenarios de export combinatorio ---
def _load_long_df(db_path: str) -> pd.DataFrame:
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
@pytest.mark.export
def test_export_modes_cartesian_combinations(canonical_validation_workspace: Dict[str, Path]) -> None:
    # --- NEW: cobre combinacoes de BAY/TERMINAL/VAR em CSV long+wide+XLSX ---
    db_path = str(canonical_validation_workspace["db_path"])
    out_dir = canonical_validation_workspace["exports"] / "combinatorial_exports"
    out_dir.mkdir(parents=True, exist_ok=True)

    long_df = _load_long_df(db_path)
    assert not long_df.empty

    bay_domains = [["BAY_A"], ["BAY_A", "BAY_B"]]
    terminal_domains = [["Terminal1"], ["Terminal1", "Terminal2"]]
    var_domains = [["IA"], ["IA", "IB"]]

    executed = 0
    for bays, terms, vars_sel in itertools.product(bay_domains, terminal_domains, var_domains):
        df_case = long_df[
            long_df["BAY"].astype(str).isin(bays)
            & long_df["TERMINAL"].astype(str).isin(terms)
            & long_df["var"].astype(str).isin(vars_sel)
        ].copy()
        if df_case.empty:
            continue

        case_id = f"b{len(bays)}_t{len(terms)}_v{len(vars_sel)}_{uuid.uuid4().hex[:6]}"
        long_csv = out_dir / f"{case_id}_long.csv"
        wide_csv = out_dir / f"{case_id}_wide.csv"
        xlsx_out = out_dir / f"{case_id}.xlsx"

        # CSV LONG
        df_case.to_csv(long_csv, index=False)
        assert long_csv.exists()
        assert not pd.read_csv(long_csv).empty

        # CSV WIDE
        wide = (
            df_case.pivot_table(
                index=["timestamp", "SE", "BAY", "TERMINAL", "equip_id"],
                columns="var",
                values="valor",
                aggfunc="last",
            )
            .reset_index()
        )
        wide.to_csv(wide_csv, index=False)
        assert wide_csv.exists()
        assert not pd.read_csv(wide_csv).empty

        # XLSX (via motor real)
        df_agg = aggregate_long(df_case, agg="max", time_floor=None)
        out_file, warns = construir_bi_excel_multi_equip_multi_var_long(
            long_df=df_agg,
            xlsx_out=str(xlsx_out),
            report_meta={"case_id": case_id},
            selected_pairs=[("TR-1", v) for v in vars_sel],
        )
        assert Path(out_file).exists()
        assert isinstance(warns, list)
        executed += 1

    # dominio 2x2x2: todas combinacoes devem gerar massa nesta fixture
    assert executed == 8
