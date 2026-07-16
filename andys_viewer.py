from __future__ import annotations

import os
import sys
import argparse
from typing import List, Optional

import duckdb
import pandas as pd
from config import DEFAULT_WORK_ROOT, get_db_path


DEFAULT_DB = get_db_path(DEFAULT_WORK_ROOT)


def sql_quote(s: str) -> str:
    return "'" + str(s).replace("'", "''") + "'"


def connect(db_path: str) -> duckdb.DuckDBPyConnection:
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Não achei o DuckDB em: {db_path}")
    con = duckdb.connect(db_path)
    con.execute("PRAGMA threads=4;")
    return con


def show_overview(con: duckdb.DuckDBPyConnection) -> None:
    print("\n=== ANDY'S OVERVIEW ===")

    # Range global de tempo + contagem
    df = con.execute("""
        SELECT
          COUNT(*) AS rows_total,
          MIN(timestamp) AS ts_min,
          MAX(timestamp) AS ts_max,
          COUNT(DISTINCT equip_id) AS equips_distintos,
          COUNT(DISTINCT var) AS vars_distintas
        FROM medicoes;
    """).df()
    print(df.to_string(index=False))

    # Linhas por ano/mes
    df2 = con.execute("""
        SELECT ano, mes, COUNT(*) AS rows
        FROM medicoes
        GROUP BY ano, mes
        ORDER BY ano, mes;
    """).df()
    print("\n--- Linhas por mês (ano/mes) ---")
    print(df2.to_string(index=False))

    # Variáveis disponíveis
    df3 = con.execute("""
        SELECT var, classe, COUNT(*) AS rows
        FROM medicoes
        GROUP BY var, classe
        ORDER BY rows DESC;
    """).df()
    print("\n--- Variáveis disponíveis ---")
    print(df3.to_string(index=False))

    # Top equips
    df4 = con.execute("""
        SELECT equip_id, COUNT(*) AS rows
        FROM medicoes
        GROUP BY equip_id
        ORDER BY rows DESC
        LIMIT 20;
    """).df()
    print("\n--- Top 20 equipamentos por volume ---")
    print(df4.to_string(index=False))


def sample_rows(con: duckdb.DuckDBPyConnection, n: int = 20) -> None:
    df = con.execute(f"""
        SELECT timestamp, equip_id, var, classe, valor, ano, mes
        FROM medicoes
        ORDER BY timestamp ASC
        LIMIT {int(n)};
    """).df()
    print("\n=== AMOSTRA (início do tempo) ===")
    print(df.to_string(index=False))


def search_equip(con: duckdb.DuckDBPyConnection, pattern: str, limit: int = 50) -> None:
    # busca case-insensitive
    pattern_sql = str(pattern).replace("'", "''")
    df = con.execute(f"""
        SELECT equip_id, COUNT(*) AS rows, MIN(timestamp) AS ts_min, MAX(timestamp) AS ts_max
        FROM medicoes
        WHERE LOWER(equip_id) LIKE '%' || LOWER('{pattern_sql}') || '%'
        GROUP BY equip_id
        ORDER BY rows DESC
        LIMIT {int(limit)};
    """).df()
    print(f"\n=== EQUIP SEARCH: '{pattern}' ===")
    if df.empty:
        print("Nada encontrado.")
        return
    print(df.to_string(index=False))


def equip_info(con: duckdb.DuckDBPyConnection, equip_id: str) -> None:
    e = str(equip_id).replace("'", "''")
    df = con.execute(f"""
        SELECT
          equip_id,
          COUNT(*) AS rows,
          MIN(timestamp) AS ts_min,
          MAX(timestamp) AS ts_max,
          COUNT(DISTINCT var) AS vars_distintas
        FROM medicoes
        WHERE equip_id = '{e}'
        GROUP BY equip_id;
    """).df()

    print(f"\n=== INFO DO EQUIP: {equip_id} ===")
    if df.empty:
        print("Equipamento não encontrado.")
        return
    print(df.to_string(index=False))

    df2 = con.execute(f"""
        SELECT var, classe, COUNT(*) AS rows
        FROM medicoes
        WHERE equip_id = '{e}'
        GROUP BY var, classe
        ORDER BY rows DESC;
    """).df()
    print("\n--- Variáveis desse equipamento ---")
    print(df2.to_string(index=False))


def query_recorte(
    con: duckdb.DuckDBPyConnection,
    equips: List[str],
    t0: str,
    t1: str,
    vars_: Optional[List[str]] = None,
    as_wide: bool = True,
) -> pd.DataFrame:
    equips_sql = "(" + ",".join([sql_quote(e) for e in equips]) + ")"
    var_filter = ""
    if vars_:
        vv = "(" + ",".join([sql_quote(v) for v in vars_]) + ")"
        var_filter = f" AND var IN {vv} "

    df = con.execute(f"""
        SELECT timestamp, equip_id, var, classe, valor
        FROM medicoes
        WHERE equip_id IN {equips_sql}
          AND timestamp >= TIMESTAMP '{t0}'
          AND timestamp <= TIMESTAMP '{t1}'
          {var_filter}
        ORDER BY timestamp ASC;
    """).df()

    if not as_wide:
        return df

    if df.empty:
        return df

    df["key"] = df["equip_id"].astype(str) + "|" + df["var"].astype(str)
    wide = df.pivot_table(index="timestamp", columns="key", values="valor", aggfunc="last").reset_index()
    return wide


def plot_wide(df_wide: pd.DataFrame, max_series: int = 12) -> None:
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError:
        print("matplotlib nao instalado. Instale com: pip install matplotlib")
        return

    if df_wide.empty:
        print("Nada para plotar (df vazio).")
        return
    if "timestamp" not in df_wide.columns:
        print("DataFrame não parece WIDE (sem coluna timestamp).")
        return

    cols = [c for c in df_wide.columns if c != "timestamp"]
    cols = cols[:max_series]

    x = pd.to_datetime(df_wide["timestamp"], errors="coerce")
    plt.figure()
    for c in cols:
        plt.plot(x, df_wide[c], label=c)
    plt.xlabel("timestamp")
    plt.ylabel("valor")
    plt.title("Andy’s Recorte (até 12 séries)")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.show()


def main():
    ap = argparse.ArgumentParser(description="Andy’s Viewer — explorar o lake DuckDB/Parquet")
    ap.add_argument("--db", default=DEFAULT_DB, help="Caminho do andys.duckdb")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("overview", help="Resumo geral do lake")
    p = sub.add_parser("sample", help="Amostra de linhas (início do tempo)")
    p.add_argument("--n", type=int, default=20)

    p = sub.add_parser("search", help="Buscar equipamentos por padrão (contains)")
    p.add_argument("pattern")
    p.add_argument("--limit", type=int, default=50)

    p = sub.add_parser("equip", help="Info detalhada de um equipamento")
    p.add_argument("equip_id")

    p = sub.add_parser("query", help="Recorte por equips + intervalo (e opcional vars)")
    p.add_argument("--equip", action="append", required=True, help="Pode repetir: --equip TR-001 --equip AL-002")
    p.add_argument("--from", dest="t0", required=True, help="Ex: 2025-01-01 00:00:00")
    p.add_argument("--to", dest="t1", required=True, help="Ex: 2025-01-03 23:59:59")
    p.add_argument("--var", action="append", help="Pode repetir: --var IA --var IB (usa nomes reais 'var')")
    p.add_argument("--long", action="store_true", help="Retorna LONG ao invés de WIDE")
    p.add_argument("--plot", action="store_true", help="Plota o recorte (se WIDE)")
    p.add_argument("--out", help="Exporta CSV do recorte (ex: recorte.csv)")

    args = ap.parse_args()

    con = connect(args.db)
    try:
        if args.cmd == "overview":
            show_overview(con)

        elif args.cmd == "sample":
            sample_rows(con, n=args.n)

        elif args.cmd == "search":
            search_equip(con, args.pattern, limit=args.limit)

        elif args.cmd == "equip":
            equip_info(con, args.equip_id)

        elif args.cmd == "query":
            df = query_recorte(
                con,
                equips=args.equip,
                t0=args.t0,
                t1=args.t1,
                vars_=args.var,
                as_wide=not args.long,
            )
            print("\n=== RESULTADO ===")
            print("shape:", df.shape)
            print(df.head(20).to_string(index=False))

            if args.out:
                df.to_csv(args.out, index=False)
                print(f"\n✅ Exportado para: {args.out}")

            if args.plot and (not args.long):
                plot_wide(df)

        else:
            raise RuntimeError("Comando desconhecido")

    finally:
        con.close()


if __name__ == "__main__":
    main()
