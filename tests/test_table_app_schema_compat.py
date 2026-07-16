from __future__ import annotations

from pathlib import Path

import duckdb

from andys_table_app import query_full_long, query_page


def test_query_page_works_with_minimal_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "mini.duckdb"
    con = duckdb.connect(str(db_path))
    try:
        con.execute(
            """
            CREATE TABLE medicoes (
              timestamp TIMESTAMP,
              equip_id VARCHAR,
              var VARCHAR,
              classe VARCHAR,
              valor VARCHAR,
              ano INTEGER,
              mes INTEGER
            );
            """
        )
        con.execute(
            """
            INSERT INTO medicoes VALUES
            ('2025-01-01 00:00:00', 'TR-1', 'IA', 'COR', '14,320833166440333333333333333', 2025, 1);
            """
        )
    finally:
        con.close()

    total, df = query_page(
        db_path=str(db_path),
        where_sql="TRUE",
        where_params=tuple(),
        pagination_sql="LIMIT ? OFFSET ?",
        pagination_params=(100, 0),
        order_sql="ORDER BY timestamp ASC",
    )
    assert total == 1
    assert "SE" in df.columns
    assert "EQUIPAMENTO" in df.columns
    assert str(df.loc[0, "EQUIPAMENTO"]) == "TR-1"
    assert float(df.loc[0, "valor"]) == 14.3


def test_query_full_long_works_with_minimal_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "mini2.duckdb"
    con = duckdb.connect(str(db_path))
    try:
        con.execute(
            """
            CREATE TABLE medicoes (
              timestamp TIMESTAMP,
              equip_id VARCHAR,
              var VARCHAR,
              classe VARCHAR,
              valor DOUBLE,
              ano INTEGER,
              mes INTEGER
            );
            """
        )
        con.execute(
            """
            INSERT INTO medicoes VALUES
            ('2025-01-02 01:00:00', 'AL-2', 'P', 'POT', 55.0, 2025, 1);
            """
        )
    finally:
        con.close()

    df = query_full_long(
        db_path=str(db_path),
        where_sql="TRUE",
        where_params=tuple(),
        limit_cap=None,
    )
    assert len(df) == 1
    assert "context_quality" not in df.columns
    assert str(df.loc[0, "equip_id"]) == "AL-2"
