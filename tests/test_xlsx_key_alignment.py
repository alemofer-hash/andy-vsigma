from __future__ import annotations

import pandas as pd

from andys_table_app import _normalize_for_agg


def test_normalize_for_agg_prefers_equipamento_over_ponto_id() -> None:
    df = pd.DataFrame(
        {
            "timestamp": ["2025-01-01 00:00:00"],
            "equip_id": ["legacy-eq"],
            "EQUIPAMENTO": ["TR-1"],
            "ponto_id": ["SE1|B1|TR-1|1"],
            "var": ["IA"],
            "classe": ["COR"],
            "valor": ["10,5"],
        }
    )
    out = _normalize_for_agg(df)
    assert str(out.iloc[0]["equip_id"]) == "TR-1"
