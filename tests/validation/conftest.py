from __future__ import annotations

import itertools
import uuid
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import duckdb
import pandas as pd
import pytest

from andys_indexer import indexar_tudo


 # --- NEW: helper de timestamp BR para dataset canonico ---
def _as_ts(day: int, hh: int = 0, mm: int = 0) -> str:
    return f"{day:02d}/01/2025 {hh:02d}:{mm:02d}:00"


# --- NEW: dominio canonico finito para validacao combinatoria exaustiva ---
@pytest.fixture(scope="session")
def validation_domain() -> Dict[str, object]:
    return {
        "periods": [(2025, 1), (2025, 2), (2026, 1)],
        "se": ["SE1", "SE2"],
        "bay": ["BAY_A", "BAY_B"],
        "equip": ["TR-1", "AL-1"],
        "terminal": ["Terminal1", "Terminal2"],
        "vars_standard": ["IA", "IB", "VAB"],
        "vars_custom": ["CUSTOM_X"],
    }


# --- NEW: gerador deterministico de powerset para multiselect ---
def powerset(values: Sequence[str], include_empty: bool = True) -> List[Tuple[str, ...]]:
    out: List[Tuple[str, ...]] = []
    start = 0 if include_empty else 1
    for r in range(start, len(values) + 1):
        out.extend(tuple(c) for c in itertools.combinations(values, r))
    return out


def _build_canonical_records() -> List[Dict[str, object]]:
    # --- NEW: dataset finito com ambiguidades reais (BAY/TERMINAL/equipamento) ---
    recs: List[Dict[str, object]] = []
    ts_slots = [
        _as_ts(1, 0, 0),
        _as_ts(1, 0, 15),
        _as_ts(2, 0, 0),
    ]
    for ts in ts_slots:
        # mesmo equipamento em BAY e TERMINAL diferentes (ambiguidade real)
        recs.extend(
            [
                {
                    "E3TIMESTAMP": ts,
                    "SE": "SE1",
                    "BAY": "BAY_A",
                    "EQUIPAMENTO": "TR-1",
                    "TERMINAL": "Terminal1",
                    "IA": "10,1",
                    "IB": "11,1",
                    "VAB": "13,8",
                    "CUSTOM_X": "1,1",
                },
                {
                    "E3TIMESTAMP": ts,
                    "SE": "SE1",
                    "BAY": "BAY_B",
                    "EQUIPAMENTO": "TR-1",
                    "TERMINAL": "Terminal2",
                    "IA": "12,2",
                    "IB": "13,2",
                    "VAB": "14,2",
                    "CUSTOM_X": "2,2",
                },
                {
                    "E3TIMESTAMP": ts,
                    "SE": "SE2",
                    "BAY": "BAY_A",
                    "EQUIPAMENTO": "AL-1",
                    "TERMINAL": "Terminal1",
                    "IA": "20,1",
                    "IB": "21,1",
                    "VAB": "22,1",
                    "CUSTOM_X": "3,1",
                },
                {
                    "E3TIMESTAMP": ts,
                    "SE": "SE2",
                    "BAY": "BAY_B",
                    "EQUIPAMENTO": "AL-1",
                    "TERMINAL": "Terminal2",
                    "IA": "22,2",
                    "IB": "23,2",
                    "VAB": "24,2",
                    "CUSTOM_X": "4,2",
                },
            ]
        )

    # casos com contexto incompleto
    recs.append(
        {
            "E3TIMESTAMP": _as_ts(3, 1, 0),
            "SE": "SE1",
            "BAY": "",
            "EQUIPAMENTO": "TR-1",
            "TERMINAL": "",
            "IA": "9,9",
            "IB": "",
            "VAB": "",
            "CUSTOM_X": "0,9",
        }
    )
    return recs


# --- NEW: workspace combinatorio isolado (sem tmp_path do pytest) ---
@pytest.fixture(scope="session")
def canonical_validation_workspace() -> Dict[str, Path]:
    base = (Path.cwd() / ".validation_tmp" / "combinatorial" / f"run_{uuid.uuid4().hex[:10]}").resolve()
    source = base / "source"
    allowed = base / "allowed"
    work = allowed / "work"
    exports = base / "exports"
    source.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    exports.mkdir(parents=True, exist_ok=True)

    records = _build_canonical_records()
    df = pd.DataFrame(records)

    # 3 arquivos de entrada para exercitar combinacoes de ingestao por periodo/tipo
    df_jan = df.iloc[:6].copy()
    df_feb = df.iloc[6:12].copy()
    df_2026 = df.iloc[12:].copy()
    df_jan.to_csv(source / "Parametros eletricos - 01_2025 - Todas SEs.csv", sep=";", index=False, encoding="utf-8")
    df_feb.to_excel(source / "Parametros eletricos - 02_2025 - Todas SEs.xlsx", index=False)
    df_2026.to_csv(source / "Parametros eletricos - 01_2026 - Todas SEs.csv", sep=";", index=False, encoding="utf-8")

    indexar_tudo(source_root=str(source), work_root=str(work), allowed_root=str(allowed))
    lake = work / "ANDYS_LAKE"
    db_path = lake / "andys.duckdb"
    assert db_path.exists()

    return {
        "base": base,
        "source": source,
        "allowed": allowed,
        "work": work,
        "lake": lake,
        "db_path": db_path,
        "exports": exports,
    }


# --- NEW: helper de execucao SQL para simplificar asserts combinatorios ---
@pytest.fixture()
def run_sql(canonical_validation_workspace: Dict[str, Path]):
    db_path = str(canonical_validation_workspace["db_path"])

    def _run(sql: str, params: Iterable[object] = ()) -> List[Tuple[object, ...]]:
        con = duckdb.connect(db_path, read_only=True)
        try:
            return con.execute(sql, list(params)).fetchall()
        finally:
            con.close()

    return _run
