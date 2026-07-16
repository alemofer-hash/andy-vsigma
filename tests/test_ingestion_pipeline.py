from __future__ import annotations

from pathlib import Path

import pandas as pd

from andys_indexer import (
    build_ponto_id,
    indexar_tudo,
    listar_arquivos_brutos,
    ler_para_canonico_e_long,
    normalize_columns,
    parse_terminal_from_identificador,
)
from db.query_builder import build_filters


def test_normalize_columns_maps_synonyms() -> None:
    df = pd.DataFrame(columns=["Subestação", "bay", "equip", "terminal", "E3TIMESTAMP"])
    out = normalize_columns(df)
    assert "SE" in out.columns
    assert "BAY" in out.columns
    assert "EQUIPAMENTO" in out.columns
    assert "TERMINAL" in out.columns
    assert "TIMESTAMP" in out.columns


def test_build_ponto_id_handles_missing_bay_terminal() -> None:
    pid = build_ponto_id("SE_A", "", "TR-1", "")
    assert pid == "SE_A|-|TR-1|-"


def test_parse_terminal_from_identificador_extracts_terminal() -> None:
    assert parse_terminal_from_identificador("SE1 BAYA TR-1 Terminal 2") == "2"


def test_integration_union_multiple_csv_schemas(tmp_path: Path) -> None:
    p1 = tmp_path / "ParÃ¢metros elÃ©tricos - 01_2025 - Todas SEs.csv"
    p2 = tmp_path / "ParÃ¢metros elÃ©tricos - 02_2025 - Todas SEs.csv"

    p1.write_text(
        "Subestacao;Bay;Equipamento;Terminal;E3TIMESTAMP;IA;EXTRA_A\n"
        "SE1;B1;TR-1;1;2025-01-01 00:00:00;10,5;foo\n",
        encoding="latin1",
    )
    p2.write_text(
        "SE,BAY,EQUIPAMENTO,TERMINAL,TIMESTAMP,IA,EXTRA_B\n"
        "SE1,B1,TR-1,2,2025-02-01 00:00:00,11.5,bar\n",
        encoding="utf-8",
    )

    canon1, _ = ler_para_canonico_e_long(str(p1))
    canon2, _ = ler_para_canonico_e_long(str(p2))
    merged = pd.concat([canon1, canon2], ignore_index=True, sort=False)

    assert "EXTRA_A" in merged.columns
    assert "EXTRA_B" in merged.columns
    assert "SE" in merged.columns
    assert "BAY" in merged.columns
    assert "EQUIPAMENTO" in merged.columns
    assert "TERMINAL" in merged.columns
    assert "ponto_id" in merged.columns


def test_build_filters_with_context_keys() -> None:
    where_sql, params = build_filters(
        equips_selected=[],
        equip_like="TR-1",
        vars_sel=["IA"],
        se_sel=["SE1"],
        bay_sel=["B1"],
        equipamento_sel=["TR-1"],
        terminal_sel=["1"],
        advanced_equals={},
        advanced_ranges={},
        ano=2025,
        mes=1,
        t0="2025-01-01 00:00:00",
        t1="2025-01-31 23:59:59",
    )
    assert "SE IN" in where_sql
    assert "BAY IN" in where_sql
    assert "EQUIPAMENTO IN" in where_sql
    assert "TERMINAL" in where_sql
    assert len(params) > 0


def test_indexer_reads_from_source_and_writes_only_to_work_root(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    work_parent = tmp_path / "allowed"
    work_root = work_parent / "work"
    source_root.mkdir(parents=True)
    work_root.mkdir(parents=True)

    src_file = source_root / "Parametros eletricos - 03_2025 - Todas SEs.csv"
    src_file.write_text(
        "SE,BAY,EQUIPAMENTO,TERMINAL,TIMESTAMP,IA\n"
        "SE1,B1,TR-1,1,2025-03-01 00:00:00,10.5\n",
        encoding="utf-8",
    )

    indexar_tudo(
        source_root=str(source_root),
        work_root=str(work_root),
        allowed_root=str(work_parent),
    )

    lake = work_root / "ANDYS_LAKE"
    assert (lake / "manifest.json").exists()
    assert (lake / "andys.duckdb").exists()
    assert list((lake / "ano=2025").rglob("medicoes_*.parquet"))
    assert list((lake / "canonico" / "ano=2025").rglob("medicoes_canon_*.parquet"))
    assert not (source_root / "manifest.json").exists()


def test_listar_arquivos_brutos_busca_subpastas_anos(tmp_path: Path) -> None:
    source = tmp_path / "ELIPSE"
    (source / "2023").mkdir(parents=True)
    (source / "2025").mkdir(parents=True)
    (source / "2026").mkdir(parents=True)
    f2023 = source / "2023" / "medicoes_2023.csv"
    f2025 = source / "2025" / "medicoes_2025.csv"
    f2026 = source / "2026" / "medicoes_2026.csv"
    for f in [f2023, f2025, f2026]:
        f.write_text("E3TIMESTAMP;EQUIPAMENTO;IA\n01/01/2025;TR-1;10,5\n", encoding="utf-8")
    files = listar_arquivos_brutos(str(source))
    files_set = set(files)
    assert str(f2023) in files_set
    assert str(f2025) in files_set
    assert str(f2026) in files_set


def test_csv_captura_colunas_vab_vbc_vca_in_fp(tmp_path: Path) -> None:
    p = tmp_path / "leituras_2023.csv"
    p.write_text(
        "E3TIMESTAMP;SE;BAY;EQUIPAMENTO;TERMINAL;VAB;VBC;VCA;IA;IB;IC;IN;P;Q;VA;VB;VC;FP\n"
        "01/01/2023 00:00:00;TOR;AL5;52-3;Terminal1;230,1;231,2;232,3;187,8;189,8;196,9;10,2;7,11;3,04;127,1;126,8;126,9;0,98\n",
        encoding="utf-8",
    )
    canon, long_df = ler_para_canonico_e_long(str(p))
    assert not canon.empty
    assert long_df["timestamp"].notna().all()
    vars_found = set(long_df["var"].astype(str).tolist())
    for expected in {"VAB", "VBC", "VCA", "IN", "FP", "IA", "P", "Q"}:
        assert expected in vars_found
