from __future__ import annotations

from andys_table_app import _is_safe_filter_col, _quote_ident


def test_quote_ident_handles_special_chars() -> None:
    assert _quote_ident('Unnamed: 18') == '"Unnamed: 18"'
    assert _quote_ident('a"b') == '"a""b"'


def test_is_safe_filter_col_blocks_non_alnum_underscore() -> None:
    assert _is_safe_filter_col("IA_1")
    assert not _is_safe_filter_col("Unnamed: 18")
