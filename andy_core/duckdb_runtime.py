from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_DUCKDB_THREADS = "2"
DEFAULT_DUCKDB_MEMORY_LIMIT = "4GB"


def _sql_quote_text(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _default_temp_directory(db_path: str | os.PathLike[str] | None = None) -> Path:
    if db_path:
        db_parent = Path(db_path).expanduser().resolve().parent
        workspace = db_parent.parent if db_parent.name.upper() == "ANDYS_LAKE" else db_parent
        return (workspace / "cache" / "duckdb_tmp").resolve()
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return (Path(local_appdata) / "ANDY" / "duckdb_tmp").resolve()
    return (Path(tempfile.gettempdir()) / "ANDY" / "duckdb_tmp").resolve()


def configure_duckdb_connection(con: Any, *, db_path: str | os.PathLike[str] | None = None) -> None:
    """Apply conservative DuckDB settings for local interactive workloads."""
    threads = str(os.environ.get("ANDYS_DUCKDB_THREADS", DEFAULT_DUCKDB_THREADS)).strip() or DEFAULT_DUCKDB_THREADS
    memory_limit = (
        str(os.environ.get("ANDYS_DUCKDB_MEMORY_LIMIT", DEFAULT_DUCKDB_MEMORY_LIMIT)).strip()
        or DEFAULT_DUCKDB_MEMORY_LIMIT
    )
    temp_dir_raw = str(os.environ.get("ANDYS_DUCKDB_TEMP_DIR", "")).strip()
    temp_dir = Path(temp_dir_raw).expanduser().resolve() if temp_dir_raw else _default_temp_directory(db_path)
    temp_dir.mkdir(parents=True, exist_ok=True)

    settings = [
        f"SET threads={int(threads)}",
        "SET preserve_insertion_order=false",
        f"SET memory_limit={_sql_quote_text(memory_limit)}",
        f"SET temp_directory={_sql_quote_text(str(temp_dir))}",
    ]
    for sql in settings:
        con.execute(sql)
