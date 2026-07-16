from __future__ import annotations

import itertools
from pathlib import Path

import pandas as pd
import pytest

from andys_indexer import ler_para_canonico_e_long


# --- NEW: gera dataset minimo por combinacao de ingestao ---
def _mk_rows(*, with_custom: bool, context_state: str) -> pd.DataFrame:
    bay = "BAY_A" if context_state == "complete" else ""
    terminal = "Terminal1" if context_state == "complete" else ""
    data = {
        "E3TIMESTAMP": ["01/01/2025 00:00:00", "01/01/2025 00:15:00"],
        "SE": ["SE1", "SE1"],
        "BAY": [bay, bay],
        "EQUIPAMENTO": ["TR-1", "TR-1"],
        "TERMINAL": [terminal, terminal],
        "IA": ["10,0", "10,5"],
        "IB": ["11,0", "11,5"],
        "VAB": ["13,8", "13,9"],
    }
    if with_custom:
        data["CUSTOM_VAR"] = ["7,2", "7,5"]
    return pd.DataFrame(data)


@pytest.mark.validation
@pytest.mark.combinatorial
@pytest.mark.integration
@pytest.mark.parametrize(
    ("source_type", "varset", "context_state"),
    list(itertools.product(["csv", "xlsx"], ["standard", "standard_plus_custom"], ["complete", "blank_context"])),
)
def test_ingestion_cartesian_combinations(
    source_type: str,
    varset: str,
    context_state: str,
    canonical_validation_workspace,
) -> None:
    # --- NEW: cobre produto cartesiano de formato/variaveis/contexto ---
    with_custom = varset == "standard_plus_custom"
    df = _mk_rows(with_custom=with_custom, context_state=context_state)

    out_dir = canonical_validation_workspace["base"] / "ingestion_cases"
    out_dir.mkdir(parents=True, exist_ok=True)
    fp = out_dir / f"case_{source_type}_{varset}_{context_state}.{source_type}"

    if source_type == "csv":
        df.to_csv(fp, sep=";", index=False, encoding="utf-8")
    else:
        df.to_excel(fp, index=False)

    canon, long_df = ler_para_canonico_e_long(str(fp))
    assert not canon.empty
    assert not long_df.empty
    assert long_df["timestamp"].notna().any()
    assert {"IA", "IB", "VAB"}.issubset(set(long_df["var"].astype(str)))

    if with_custom and source_type == "csv":
        assert "CUSTOM_VAR" in set(long_df["var"].astype(str))
    else:
        assert {"IA", "IB", "VAB"}.issubset(set(long_df["var"].astype(str)))

    if context_state == "blank_context":
        bay_norm = canon["BAY"].fillna("").astype(str).str.strip().str.lower()
        assert bay_norm.isin(["", "nan", "none", "-"]).all()
