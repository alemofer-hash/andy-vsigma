from __future__ import annotations

import datetime as dt
import json
import logging
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping

import duckdb


RUNTIME_STATE_VERSION = 1
WORKSPACE_SCHEMA_VERSION = 1
CATALOG_SCHEMA_VERSION = 1
RUNTIME_STATE_FILENAME = "runtime_state.json"
REQUIRED_CATALOG_OBJECTS = ("medicoes", "medicoes_canon")


def get_runtime_state_path(layout: Mapping[str, Path]) -> Path:
    return (Path(layout["app_root"]).resolve() / "config" / RUNTIME_STATE_FILENAME).resolve()


def _read_release_text(path: Path) -> str:
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return ""
    return str(raw).strip()


def _read_build_info(path: Path) -> dict[str, str]:
    raw = _read_release_text(path)
    if not raw:
        return {}
    out: dict[str, str] = {}
    for line in raw.splitlines():
        text = str(line).strip()
        if not text or "=" not in text:
            continue
        key, value = text.split("=", 1)
        out[str(key).strip()] = str(value).strip()
    return out


def detect_install_root() -> Path:
    if bool(getattr(sys, "frozen", False)):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def detect_release_metadata() -> dict[str, Any]:
    install_root = detect_install_root()
    version_file = (install_root / "VERSION.txt").resolve()
    build_info_file = (install_root / "BUILD_INFO.txt").resolve()
    build_info = _read_build_info(build_info_file)
    version = str(build_info.get("version", "")).strip() or _read_release_text(version_file)
    executable_path = ""
    try:
        executable_path = str(Path(sys.executable).resolve())
    except Exception:
        executable_path = ""
    return {
        "install_root": str(install_root),
        "version": version,
        "build_info": build_info,
        "build_info_path": str(build_info_file),
        "version_path": str(version_file),
        "is_frozen": bool(getattr(sys, "frozen", False)),
        "executable_path": executable_path,
        "detected_at": dt.datetime.now().isoformat(timespec="seconds"),
    }


def _normalize_runtime_state(payload: Mapping[str, Any] | None, layout: Mapping[str, Path]) -> dict[str, Any]:
    raw = dict(payload or {})
    release = raw.get("release")
    if not isinstance(release, dict):
        release = {}
    startup = raw.get("last_startup_check")
    if not isinstance(startup, dict):
        startup = {}
    catalog = raw.get("last_catalog_state")
    if not isinstance(catalog, dict):
        catalog = {}
    migrations = raw.get("applied_migrations")
    if not isinstance(migrations, list):
        migrations = []

    detected_release = detect_release_metadata()
    merged_release = dict(detected_release)
    merged_release.update({str(k): v for k, v in dict(release).items()})
    # The currently running release metadata always wins for path/version detection.
    merged_release.update(detected_release)

    return {
        "state_version": int(raw.get("state_version", RUNTIME_STATE_VERSION)),
        "workspace_schema_version": int(raw.get("workspace_schema_version", WORKSPACE_SCHEMA_VERSION)),
        "catalog_schema_version": int(raw.get("catalog_schema_version", CATALOG_SCHEMA_VERSION)),
        "app_root": str(Path(layout["app_root"]).resolve()),
        "workspace_root": str(Path(layout["workspace"]).resolve()),
        "db_path": str(Path(layout["db_path"]).resolve()),
        "release": merged_release,
        "last_startup_check": dict(startup),
        "last_catalog_state": dict(catalog),
        "applied_migrations": [str(item).strip() for item in migrations if str(item).strip()],
        "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
    }


def load_runtime_state(layout: Mapping[str, Path]) -> dict[str, Any]:
    path = get_runtime_state_path(layout)
    if not path.exists():
        return _normalize_runtime_state({}, layout)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return _normalize_runtime_state({}, layout)
    if not isinstance(payload, dict):
        return _normalize_runtime_state({}, layout)
    return _normalize_runtime_state(payload, layout)


def save_runtime_state(layout: Mapping[str, Path], state: Mapping[str, Any]) -> Path:
    path = get_runtime_state_path(layout)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_runtime_state(state, layout)
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return path


def ensure_runtime_state(layout: Mapping[str, Path], logger: logging.Logger | None = None) -> dict[str, Any]:
    state = load_runtime_state(layout)
    if not state.get("applied_migrations"):
        state["applied_migrations"] = ["runtime_state_v1"]
    save_runtime_state(layout, state)
    if logger is not None:
        logger.info(
            "Runtime state ready: path=%s install_root=%s version=%s",
            get_runtime_state_path(layout),
            state.get("release", {}).get("install_root", ""),
            state.get("release", {}).get("version", ""),
        )
    return state


def inspect_local_catalog(layout: Mapping[str, Path]) -> dict[str, Any]:
    lake_root = Path(layout["lake"]).resolve()
    db_path = Path(layout["db_path"]).resolve()
    manifest_path = (lake_root / "manifest.json").resolve()
    long_parts = sorted(lake_root.glob("ano=*/mes=*/medicoes_*.parquet"))
    canon_parts = sorted(lake_root.glob("canonico/ano=*/mes=*/medicoes_canon_*.parquet"))

    manifest_exists = manifest_path.exists()
    manifest_valid = False
    manifest_file_count = 0
    manifest_error = ""
    if manifest_exists:
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            files = payload.get("files") if isinstance(payload, dict) else {}
            manifest_file_count = len(files) if isinstance(files, dict) else 0
            manifest_valid = isinstance(payload, dict)
        except Exception as exc:
            manifest_error = exc.__class__.__name__

    db_exists = db_path.exists()
    db_ready = False
    db_error = ""
    catalog_object_types: dict[str, str] = {}
    if db_exists:
        try:
            con = duckdb.connect(str(db_path), read_only=True)
            try:
                rows = con.execute(
                    """
                    SELECT table_name, table_type
                    FROM information_schema.tables
                    WHERE table_schema = current_schema()
                    """
                ).fetchall()
                catalog_object_types = {
                    str(name).lower(): str(table_type).upper()
                    for name, table_type in rows
                }
                for object_name in REQUIRED_CATALOG_OBJECTS:
                    if object_name not in catalog_object_types:
                        raise RuntimeError(f"missing:{object_name}")
                    con.execute(f'SELECT * FROM "{object_name}" LIMIT 1').fetchall()
                db_ready = True
            finally:
                con.close()
        except Exception as exc:
            db_error = exc.__class__.__name__

    return {
        "lake_root": str(lake_root),
        "db_path": str(db_path),
        "db_exists": bool(db_exists),
        "db_ready": bool(db_ready),
        "db_error": db_error,
        "catalog_object_types": dict(catalog_object_types),
        "manifest_path": str(manifest_path),
        "manifest_exists": bool(manifest_exists),
        "manifest_valid": bool(manifest_valid),
        "manifest_error": manifest_error,
        "manifest_file_count": int(manifest_file_count),
        "long_parquet_count": int(len(long_parts)),
        "canon_parquet_count": int(len(canon_parts)),
        "lake_usable": bool(long_parts and canon_parts),
        "checked_at": dt.datetime.now().isoformat(timespec="seconds"),
    }


def _backup_existing_db(layout: Mapping[str, Path], db_path: Path) -> str:
    cache_root = (Path(layout["cache"]).resolve() / "db_backups").resolve()
    cache_root.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    backup_path = (cache_root / f"andys_pre_repair_{stamp}.duckdb").resolve()
    shutil.move(str(db_path), str(backup_path))
    return str(backup_path)


def rebuild_catalog_from_local_lake(
    layout: Mapping[str, Path],
    *,
    source_root: str,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    from andys_indexer import construir_catalogo_duckdb

    workspace = Path(layout["workspace"]).resolve()
    app_root = Path(layout["app_root"]).resolve()
    db_path = Path(layout["db_path"]).resolve()
    backup_path = ""

    if db_path.exists():
        backup_path = _backup_existing_db(layout, db_path)
        if logger is not None:
            logger.warning("Local DB failed integrity checks; moved aside to %s before lightweight repair.", backup_path)

    construir_catalogo_duckdb(
        str(workspace),
        source_root=str(source_root),
        allowed_root=str(app_root),
    )
    inspection = inspect_local_catalog(layout)
    status = "repaired_from_local_lake" if bool(inspection.get("db_ready", False)) else "repair_failed"
    result = dict(inspection)
    result["status"] = status
    result["backup_db_path"] = backup_path
    result["repair_source"] = "local_lake"
    return result


def record_runtime_event(
    layout: Mapping[str, Path],
    *,
    status: str,
    inspection: Mapping[str, Any],
    note: str = "",
) -> dict[str, Any]:
    state = load_runtime_state(layout)
    event = {
        "status": str(status),
        "note": str(note or ""),
        "db_ready": bool(inspection.get("db_ready", False)),
        "db_exists": bool(inspection.get("db_exists", False)),
        "lake_usable": bool(inspection.get("lake_usable", False)),
        "manifest_valid": bool(inspection.get("manifest_valid", False)),
        "manifest_file_count": int(inspection.get("manifest_file_count", 0) or 0),
        "db_error": str(inspection.get("db_error", "")),
        "checked_at": str(inspection.get("checked_at", dt.datetime.now().isoformat(timespec="seconds"))),
    }
    state["last_startup_check"] = dict(event)
    state["last_catalog_state"] = dict(inspection)
    save_runtime_state(layout, state)
    return state
