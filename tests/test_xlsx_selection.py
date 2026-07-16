from __future__ import annotations

import pytest

from xlsx_selection import expand_pairs, migrate_legacy_pairs, normalize_selections, validate_selections


def test_migrate_legacy_pairs_to_map() -> None:
    legacy = [("EQP_001", "corrente"), ("EQP_001", "tensao"), ("EQP_002", "potencia")]
    out = migrate_legacy_pairs(legacy)
    assert out == {
        "EQP_001": ["corrente", "tensao"],
        "EQP_002": ["potencia"],
    }


def test_expand_pairs_single_equip_three_vars() -> None:
    selections = {"EQP_001": ["corrente", "tensao", "potencia"]}
    pairs = expand_pairs(selections)
    assert len(pairs) == 3
    assert ("EQP_001", "corrente") in pairs
    assert ("EQP_001", "tensao") in pairs
    assert ("EQP_001", "potencia") in pairs


def test_expand_pairs_two_equips_different_vars() -> None:
    selections = {
        "EQP_001": ["corrente", "tensao"],
        "EQP_002": ["potencia"],
    }
    pairs = expand_pairs(selections)
    assert pairs == [
        ("EQP_001", "corrente"),
        ("EQP_001", "tensao"),
        ("EQP_002", "potencia"),
    ]


def test_validate_fail_fast_when_equip_without_var() -> None:
    selections = normalize_selections({"EQP_001": ["corrente"], "EQP_002": []})
    with pytest.raises(ValueError):
        validate_selections(selections, required_equips=["EQP_001", "EQP_002"])
