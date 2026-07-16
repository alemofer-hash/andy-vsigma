from __future__ import annotations

from pathlib import Path

import pytest

from config import (
    assert_readonly_source,
    ensure_db_exists,
    get_source_root,
    load_config,
    resolve_db_path,
    safe_join_root,
)


def test_safe_join_root_allows_contained_paths(tmp_path: Path) -> None:
    root = tmp_path / "root"
    target = root / "safe" / "file.txt"
    root.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    result = safe_join_root(str(root), str(target))
    assert Path(result) == target.resolve()


def test_safe_join_root_blocks_escape_paths(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside" / "file.txt"
    root.mkdir(parents=True)
    outside.parent.mkdir(parents=True)
    with pytest.raises(ValueError):
        safe_join_root(str(root), str(outside))


def test_load_config_validates_source_root_exists_and_is_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source"
    allowed = tmp_path / "allowed"
    work = allowed / "work"
    source.mkdir(parents=True)
    allowed.mkdir(parents=True)
    work.mkdir(parents=True)
    monkeypatch.setenv("ANDYS_ALLOWED_ROOT", str(allowed))
    cfg = load_config(source_root_override=str(source), work_root_override=str(work))
    assert Path(cfg.source_root) == source.resolve()


def test_load_config_rejects_output_outside_allowed_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source"
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    source.mkdir(parents=True)
    allowed.mkdir(parents=True)
    outside.mkdir(parents=True)
    monkeypatch.setenv("ANDYS_ALLOWED_ROOT", str(allowed))
    with pytest.raises(ValueError):
        load_config(source_root_override=str(source), work_root_override=str(outside))


def test_assert_readonly_source_blocks_write_attempt(tmp_path: Path) -> None:
    source = tmp_path / "ELIPSE"
    source.mkdir(parents=True)
    source_s = str(source.resolve())
    with pytest.raises(PermissionError):
        assert_readonly_source(str(source / "file.tmp"), source_s, mode="wb")
    # leitura deve ser permitida
    assert_readonly_source(str(source / "file.csv"), source_s, mode="rb")


def test_source_root_trailing_dot_is_normalized_in_memory(tmp_path: Path) -> None:
    source = tmp_path / "ELIPSE"
    source.mkdir(parents=True)
    normalized = get_source_root(str(source) + ".")
    assert Path(normalized) == source.resolve()


def test_config_resolve_db_path_default(tmp_path: Path) -> None:
    source = tmp_path / "source"
    allowed = tmp_path / "allowed"
    work = allowed / "work"
    lake = work / "ANDYS_LAKE"
    source.mkdir(parents=True)
    lake.mkdir(parents=True)
    resolved = resolve_db_path(
        work_root=str(work),
        lake_root=str(lake),
        db_path_override=None,
        allowed_root=str(allowed),
        source_root=str(source),
    )
    assert Path(resolved) == (lake / "andys.duckdb").resolve()


def test_config_resolve_db_path_env(tmp_path: Path) -> None:
    source = tmp_path / "source"
    allowed = tmp_path / "allowed"
    work = allowed / "work"
    source.mkdir(parents=True)
    work.mkdir(parents=True)
    env_db = allowed / "dbs" / "custom.duckdb"
    env_db.parent.mkdir(parents=True)
    resolved = resolve_db_path(
        work_root=str(work),
        db_path_override=str(env_db),
        allowed_root=str(allowed),
        source_root=str(source),
    )
    assert Path(resolved) == env_db.resolve()

    with pytest.raises(ValueError, match="\\.duckdb"):
        resolve_db_path(
            work_root=str(work),
            db_path_override=str(allowed / "dbs" / "custom.db"),
            allowed_root=str(allowed),
            source_root=str(source),
        )


def test_config_blocks_db_outside_allowed_root(tmp_path: Path) -> None:
    source = tmp_path / "source"
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside" / "x.duckdb"
    work = allowed / "work"
    source.mkdir(parents=True)
    work.mkdir(parents=True)
    outside.parent.mkdir(parents=True)
    with pytest.raises(ValueError, match="raiz permitida|ALLOWED_ROOT|fora"):
        resolve_db_path(
            work_root=str(work),
            db_path_override=str(outside),
            allowed_root=str(allowed),
            source_root=str(source),
        )


def test_ensure_db_exists_has_actionable_message(tmp_path: Path) -> None:
    missing = tmp_path / "nope.duckdb"
    with pytest.raises(FileNotFoundError, match="andys_indexer\\.py"):
        ensure_db_exists(str(missing), lake_root=str(tmp_path / "ANDYS_LAKE"))
