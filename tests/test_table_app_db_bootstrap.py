from __future__ import annotations

from pathlib import Path

import pytest

from andys_table_app import resolve_db_for_app
from config import load_config


def _mk_cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source = tmp_path / "source"
    allowed = tmp_path / "allowed"
    work = allowed / "work"
    lake = work / "ANDYS_LAKE"
    source.mkdir(parents=True)
    lake.mkdir(parents=True)
    monkeypatch.setenv("ANDYS_ENV", "dev")
    monkeypatch.setenv("ANDYS_ALLOWED_ROOT", str(allowed))
    cfg = load_config(source_root_override=str(source), work_root_override=str(work))
    return cfg, lake


def test_table_app_missing_db_shows_actionable_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg, _ = _mk_cfg(tmp_path, monkeypatch)
    with pytest.raises(FileNotFoundError, match="andys_indexer\\.py"):
        resolve_db_for_app(cfg, auto_detect=False)


def test_table_app_autodetects_single_db_in_lake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg, lake = _mk_cfg(tmp_path, monkeypatch)
    detected = lake / "nested" / "andys.duckdb"
    detected.parent.mkdir(parents=True)
    detected.touch()

    db_path, diag = resolve_db_for_app(cfg, auto_detect=True)
    assert Path(db_path) == detected.resolve()
    assert bool(diag.get("autodetect_used")) is True
