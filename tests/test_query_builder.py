from __future__ import annotations

import pytest

from db.query_builder import build_filters, build_order_by


def test_build_order_by_rejects_non_allowlisted_column() -> None:
    allow = {"timestamp": "timestamp", "equip_id": "equip_id"}
    with pytest.raises(ValueError):
        build_order_by("valor", "ASC", allow)


def test_build_filters_uses_params_not_string_concatenation() -> None:
    sql, params = build_filters(
        equips_selected=[],
        equip_like="abc' OR 1=1 --",
        vars_sel=["P"],
        ano=2025,
        mes=1,
        t0="2025-01-01 00:00:00",
        t1="2025-01-31 23:59:59",
    )
    assert "OR 1=1" not in sql
    assert "abc' OR 1=1 --" not in sql
    assert "?" in sql
    assert any("1=1" in str(p) for p in params)


def test_build_filters_accepts_string_month_with_leading_zero() -> None:
    sql, params = build_filters(
        equips_selected=[],
        equip_like="TR-1",
        vars_sel=[],
        ano=2025,
        mes="01",
        t0=None,
        t1=None,
    )
    assert "mes = ?" in sql
    assert 1 in params
