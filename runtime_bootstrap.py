from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path


# --- NEW: SQL schema used to create a valid empty runtime DB on first launch ---
_EMPTY_DB_SQL = (
    """
    CREATE TABLE IF NOT EXISTS medicoes (
        timestamp TIMESTAMP,
        ano INTEGER,
        mes INTEGER,
        SE VARCHAR,
        BAY VARCHAR,
        EQUIPAMENTO VARCHAR,
        TERMINAL VARCHAR,
        IDENTIFICADOR_RAW VARCHAR,
        ponto_id VARCHAR,
        context_quality VARCHAR,
        parsed_terminal_ok BOOLEAN,
        equip_id VARCHAR,
        var VARCHAR,
        classe VARCHAR,
        valor DOUBLE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS medicoes_canon (
        TIMESTAMP TIMESTAMP,
        SE VARCHAR,
        BAY VARCHAR,
        EQUIPAMENTO VARCHAR,
        TERMINAL VARCHAR,
        IDENTIFICADOR_RAW VARCHAR,
        ponto_id VARCHAR,
        context_quality VARCHAR,
        parsed_terminal_ok BOOLEAN
    );
    """,
)


# --- NEW: discover optional bundled DB seed candidates ---
def _seed_db_candidates() -> list[Path]:
    roots: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(str(meipass)).resolve())
    roots.append(Path(__file__).resolve().parent)

    rels = (
        "andys_seed.duckdb",
        "seed/andys_seed.duckdb",
        "seed/andys.duckdb",
        "assets/andys_seed.duckdb",
    )
    out: list[Path] = []
    for root in roots:
        for rel in rels:
            p = (root / rel).resolve()
            if p not in out:
                out.append(p)
    return out


# --- NEW: quick check for user-provided source files in source_inbox ---
def _has_source_files(source_root: Path) -> bool:
    if not source_root.exists():
        return False
    for pattern in ("*.csv", "*.xlsx", "*.xlsm"):
        if next(source_root.rglob(pattern), None) is not None:
            return True
    return False


def _count_source_files(source_root: Path) -> int:
    if not source_root.exists():
        return 0
    total = 0
    for pattern in ("*.csv", "*.xlsx", "*.xlsm"):
        total += sum(1 for _ in source_root.rglob(pattern))
    return int(total)


# --- NEW: create a valid empty DuckDB catalog so app startup never fails on first launch ---
def _create_empty_runtime_db(db_path: Path) -> None:
    import duckdb

    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        for stmt in _EMPTY_DB_SQL:
            con.execute(stmt)
    finally:
        con.close()


def run_index_if_needed(
    layout: dict[str, Path],
    logger: logging.Logger,
    *,
    source_root_override: Path | None = None,
) -> dict[str, str]:
    db_path = Path(layout["db_path"]).resolve()
    source_root = Path(source_root_override).resolve() if source_root_override is not None else Path(layout["source"]).resolve()
    files_count = _count_source_files(source_root)
    if files_count <= 0:
        logger.info("Runtime indexing: no source files detected under %s", source_root)
        return {
            "status": "no_source_files",
            "db_path": str(db_path),
            "source_root": str(source_root),
            "source_files": str(files_count),
        }

    logger.info("Runtime indexing: starting indexer for source_root=%s source_files=%s", source_root, files_count)
    from andys_indexer import indexar_tudo

    indexar_tudo(
        source_root=str(source_root),
        work_root=str(layout["workspace"]),
        allowed_root=str(layout["app_root"]),
    )
    if db_path.exists():
        logger.info("Runtime indexing: local DB is ready at %s", db_path)
        return {
            "status": "indexed",
            "db_path": str(db_path),
            "source_root": str(source_root),
            "source_files": str(files_count),
        }
    logger.warning("Runtime indexing: indexer completed but DB was not created at %s", db_path)
    return {
        "status": "indexer_finished_without_db",
        "db_path": str(db_path),
        "source_root": str(source_root),
        "source_files": str(files_count),
    }


def reindex_local_database(
    layout: dict[str, Path],
    logger: logging.Logger,
    *,
    source_root_override: Path | None = None,
) -> dict[str, str]:
    logger.info("Runtime indexing: forced reindex requested.")
    return run_index_if_needed(layout, logger, source_root_override=source_root_override)


# --- NEW: initialize local DB via seed copy, automatic indexing, or empty DB fallback ---
def ensure_local_db_initialized(
    layout: dict[str, Path],
    logger: logging.Logger,
    *,
    source_root_override: Path | None = None,
) -> dict[str, str]:
    db_path = Path(layout["db_path"]).resolve()
    lake_root = Path(layout["lake"]).resolve()
    source_root = Path(source_root_override).resolve() if source_root_override is not None else Path(layout["source"]).resolve()

    lake_root.mkdir(parents=True, exist_ok=True)
    if source_root == Path(layout["source"]).resolve():
        source_root.mkdir(parents=True, exist_ok=True)
    files_count = _count_source_files(source_root)

    logger.info(
        "DB bootstrap: expected_path=%s exists=%s source_root=%s source_files=%s",
        db_path,
        db_path.exists(),
        source_root,
        files_count,
    )
    if db_path.exists():
        return {"status": "existing", "db_path": str(db_path), "source_root": str(source_root), "source_files": str(files_count)}

    for seed in _seed_db_candidates():
        if seed.exists() and seed.is_file():
            db_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(seed, db_path)
            logger.info("DB bootstrap: copied bundled seed from %s to %s", seed, db_path)
            return {"status": "seed_copied", "db_path": str(db_path), "seed_path": str(seed)}

    index_result = run_index_if_needed(layout, logger, source_root_override=source_root)
    if index_result["status"] == "indexed":
        logger.info("DB bootstrap: indexer bootstrap completed successfully.")
        return index_result
    if index_result["status"] != "no_source_files":
        logger.warning("DB bootstrap: index result=%s", index_result)

    _create_empty_runtime_db(db_path)
    logger.info("DB bootstrap: created empty runtime DB at %s", db_path)
    return {"status": "empty_created", "db_path": str(db_path), "source_root": str(source_root), "source_files": str(files_count)}
