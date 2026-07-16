from __future__ import annotations

from pathlib import Path

from andys_indexer import ler_para_canonico_e_long


def test_indexer_maps_in_onto_in(tmp_path: Path) -> None:
    p = tmp_path / "drift_in.csv"
    p.write_text(
        "E3TIMESTAMP;SE;BAY;EQUIPAMENTO;TERMINAL;IN_;IA\n"
        "01/01/2023 00:00:00;TOR;AL5;52-3;Terminal1;10,2;187,8\n",
        encoding="utf-8",
    )
    _, long_df = ler_para_canonico_e_long(str(p))
    vars_found = set(long_df["var"].astype(str).tolist())
    assert "IN" in vars_found
    assert "IN_" not in vars_found
