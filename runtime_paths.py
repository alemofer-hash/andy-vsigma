from __future__ import annotations

import os
import json
import sys
from pathlib import Path
from typing import Any, Mapping


APP_DIRNAME = "ANDY"
WORKSPACE_DIRNAME = "workspace"
SOURCE_DIRNAME = "source_inbox"
LOGS_DIRNAME = "logs"
CACHE_DIRNAME = "cache"
SETTINGS_DIRNAME = "config"
SETTINGS_FILENAME = "settings.json"
SOURCE_MODE_UNSET = "unset"
SOURCE_MODE_CONFIGURED = "configured_folder"
SOURCE_MODE_LOCAL_INBOX = "local_inbox"


# --- NEW: detect frozen execution for PyInstaller path handling ---
def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


# --- NEW: resolve bundle base path in frozen/non-frozen modes ---
def get_bundle_path() -> Path:
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            return Path(str(meipass)).resolve()
    return Path(__file__).resolve().parent


# --- NEW: resolve project root for source execution ---
def get_project_root() -> Path:
    return Path(__file__).resolve().parent


# --- NEW: resolve Streamlit app file for launcher ---
def get_streamlit_app_path() -> Path:
    base = get_bundle_path() if is_frozen() else get_project_root()
    return (base / "andys_table_app.py").resolve()


# --- NEW: stable user-writable app root under LocalAppData/AppData ---
def get_user_app_dir(
    app_dirname: str = APP_DIRNAME,
    *,
    environ: Mapping[str, str] | None = None,
) -> Path:
    env = dict(os.environ) if environ is None else dict(environ)
    local = str(env.get("LOCALAPPDATA", "")).strip()
    roaming = str(env.get("APPDATA", "")).strip()
    if local:
        return (Path(local).expanduser() / app_dirname).resolve()
    if roaming:
        return (Path(roaming).expanduser() / app_dirname).resolve()
    return (Path.home() / "AppData" / "Local" / app_dirname).resolve()


# --- NEW: compute app runtime layout (workspace/log/cache/etc.) ---
def get_runtime_layout(root: Path | None = None) -> dict[str, Path]:
    app_root = (root or get_user_app_dir()).resolve()
    workspace = (app_root / WORKSPACE_DIRNAME).resolve()
    source = (app_root / SOURCE_DIRNAME).resolve()
    settings_dir = (app_root / SETTINGS_DIRNAME).resolve()
    lake = (workspace / "ANDYS_LAKE").resolve()
    exports = (workspace / "ANDYS_EXPORTS").resolve()
    logs = (app_root / LOGS_DIRNAME).resolve()
    cache = (app_root / CACHE_DIRNAME).resolve()
    db_path = (lake / "andys.duckdb").resolve()
    audit_log_path = (logs / "audit.jsonl").resolve()
    return {
        "app_root": app_root,
        "workspace": workspace,
        "source": source,
        "settings_dir": settings_dir,
        "settings_path": (settings_dir / SETTINGS_FILENAME).resolve(),
        "lake": lake,
        "exports": exports,
        "logs": logs,
        "cache": cache,
        "db_path": db_path,
        "audit_log_path": audit_log_path,
    }


# --- NEW: explicit helper for callers that only need DB path ---
def get_runtime_db_path(root: Path | None = None) -> Path:
    return get_runtime_layout(root=root)["db_path"]


# --- NEW: create runtime directories ahead of app startup ---
def ensure_runtime_dirs(layout: dict[str, Path]) -> None:
    for key in ("app_root", "workspace", "source", "settings_dir", "lake", "exports", "logs", "cache"):
        layout[key].mkdir(parents=True, exist_ok=True)


def _settings_path(root: Path | None = None) -> Path:
    return get_runtime_layout(root=root)["settings_path"]


def _normalize_packaged_settings(settings: Mapping[str, Any] | None, layout: dict[str, Path]) -> dict[str, Any]:
    payload = dict(settings or {})
    source_mode = str(payload.get("source_mode", SOURCE_MODE_UNSET)).strip().lower() or SOURCE_MODE_UNSET
    source_root = str(payload.get("source_root", "")).strip()
    if source_mode not in {SOURCE_MODE_UNSET, SOURCE_MODE_CONFIGURED, SOURCE_MODE_LOCAL_INBOX}:
        source_mode = SOURCE_MODE_CONFIGURED if source_root else SOURCE_MODE_UNSET
    payload["source_mode"] = source_mode
    payload["source_root"] = source_root
    payload.setdefault("first_run_completed", False)
    payload.setdefault("last_index", {})
    payload["config_path"] = str(layout["settings_path"])
    payload.setdefault("export_dir", str(layout["exports"]))
    payload.setdefault("logs_dir", str(layout["logs"]))
    return payload


def load_packaged_settings(root: Path | None = None) -> dict[str, Any]:
    layout = get_runtime_layout(root=root)
    path = layout["settings_path"]
    if not path.exists():
        return _normalize_packaged_settings({}, layout)
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        loaded = {}
    return _normalize_packaged_settings(loaded if isinstance(loaded, dict) else {}, layout)


def save_packaged_settings(settings: Mapping[str, Any], root: Path | None = None) -> Path:
    layout = get_runtime_layout(root=root)
    path = layout["settings_path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _normalize_packaged_settings(settings, layout)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def ensure_runtime_workspace(layout: dict[str, Path], settings: Mapping[str, Any] | None = None) -> dict[str, Any]:
    ensure_runtime_dirs(layout)
    normalized = _normalize_packaged_settings(settings or load_packaged_settings(root=layout["app_root"]), layout)
    save_packaged_settings(normalized, root=layout["app_root"])
    return normalized


def _is_valid_source_directory(path_text: str) -> bool:
    if not str(path_text or "").strip():
        return False
    candidate = Path(str(path_text).strip()).expanduser()
    return bool(candidate.is_absolute() and candidate.exists() and candidate.is_dir())


def _is_unc_path(path_text: str) -> bool:
    return str(path_text or "").strip().startswith("\\\\")


def resolve_effective_source_root(
    layout: dict[str, Path],
    *,
    settings: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    env = dict(os.environ) if environ is None else dict(environ)
    settings_map = _normalize_packaged_settings(settings or {}, layout)
    env_source = str(env.get("ANDYS_SOURCE_ROOT", "")).strip()
    if _is_valid_source_directory(env_source):
        return {
            "source_root": str(Path(env_source).expanduser()),
            "reason": "env_valid",
            "is_unc": _is_unc_path(env_source),
        }

    source_mode = str(settings_map.get("source_mode", SOURCE_MODE_UNSET)).strip().lower() or SOURCE_MODE_UNSET
    configured_source = str(settings_map.get("source_root", "")).strip()
    if source_mode == SOURCE_MODE_LOCAL_INBOX:
        source = str(layout["source"])
        return {"source_root": source, "reason": "local_inbox", "is_unc": False}

    if source_mode == SOURCE_MODE_CONFIGURED and configured_source:
        if _is_valid_source_directory(configured_source):
            return {
                "source_root": str(Path(configured_source).expanduser()),
                "reason": "settings_valid",
                "is_unc": _is_unc_path(configured_source),
            }
        return {
            "source_root": configured_source,
            "reason": "settings_unavailable",
            "is_unc": _is_unc_path(configured_source),
        }

    return {"source_root": "", "reason": SOURCE_MODE_UNSET, "is_unc": False}


# --- NEW: build packaged runtime env values consumed by config/app ---
def build_runtime_env(layout: dict[str, Path]) -> dict[str, str]:
    return {
        "ANDYS_ENV": "prod",
        "ANDYS_ALLOWED_ROOT": str(layout["workspace"]),
        "ANDYS_WORK_ROOT": str(layout["workspace"]),
        "ANDYS_SOURCE_ROOT": str(layout["source"]),
        "ANDYS_DB_PATH": str(layout["db_path"]),
        "ANDYS_EXPORT_DIR": str(layout["exports"]),
        "ANDYS_AUDIT_LOG_PATH": str(layout["audit_log_path"]),
        "ANDYS_LOG_LEVEL": "INFO",
    }
