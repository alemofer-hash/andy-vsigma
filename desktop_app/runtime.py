from __future__ import annotations

import datetime as dt
import logging
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from config import get_source_root
from runtime_bootstrap import ensure_local_db_initialized, reindex_local_database
from runtime_paths import (
    SOURCE_MODE_CONFIGURED,
    SOURCE_MODE_LOCAL_INBOX,
    SOURCE_MODE_UNSET,
    ensure_runtime_dirs,
    ensure_runtime_workspace,
    get_runtime_layout,
    load_packaged_settings,
    resolve_effective_source_root,
    save_packaged_settings,
)

from desktop_app.models import DesktopRuntimeState

try:
    from andy_version import __version__ as APP_VERSION
except Exception:
    APP_VERSION = "dev"


# --- NEW: local desktop logger bound to the user-writable runtime workspace ---
def _configure_desktop_logger(log_file: Path) -> logging.Logger:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("andy.desktop")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh = logging.FileHandler(str(log_file), encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


# --- NEW: spreadsheet discovery reused by setup/status/index flows ---
def count_spreadsheet_files(source_root: str) -> int:
    root = Path(str(source_root or "").strip()).expanduser()
    if not root.exists() or not root.is_dir():
        return 0
    total = 0
    for pattern in ("*.csv", "*.xlsx", "*.xlsm"):
        total += sum(1 for _ in root.rglob(pattern))
    return int(total)


# --- NEW: explicit installed-app setup gate that avoids accidental inbox fallback ---
def setup_required_for_desktop(settings: Mapping[str, Any], resolution: Mapping[str, Any]) -> bool:
    if str(resolution.get("reason", "")).strip() == "env_valid":
        return False
    source_mode = str(settings.get("source_mode", SOURCE_MODE_UNSET)).strip().lower() or SOURCE_MODE_UNSET
    source_root = str(settings.get("source_root", "")).strip()
    if source_mode == SOURCE_MODE_LOCAL_INBOX:
        return False
    if source_mode == SOURCE_MODE_CONFIGURED and source_root:
        candidate = Path(source_root).expanduser()
        return not (candidate.is_absolute() and candidate.exists() and candidate.is_dir())
    return True


# --- NEW: desktop settings/runtime facade over the packaged-settings helpers ---
class DesktopRuntimeService:
    def __init__(
        self,
        *,
        root: Optional[Path] = None,
        environ: Optional[Mapping[str, str]] = None,
    ) -> None:
        self.environ: Dict[str, str] = dict(os.environ) if environ is None else dict(environ)
        self.layout = get_runtime_layout(root=root)
        ensure_runtime_dirs(self.layout)
        self.logger = _configure_desktop_logger(self.layout["logs"] / "desktop_app.log")

    # --- NEW: normalized settings accessor for the installed desktop app ---
    def load_settings(self) -> Dict[str, Any]:
        return ensure_runtime_workspace(self.layout, load_packaged_settings(root=self.layout["app_root"]))

    # --- NEW: persist desktop settings with consistent metadata updates ---
    def save_settings(self, settings: Mapping[str, Any]) -> Dict[str, Any]:
        payload = dict(self.load_settings())
        payload.update(dict(settings))
        payload["updated_at"] = dt.datetime.now().isoformat(timespec="seconds")
        payload["app_version"] = APP_VERSION
        save_packaged_settings(payload, root=self.layout["app_root"])
        return self.load_settings()

    # --- NEW: source-resolution snapshot for the desktop UI/status model ---
    def load_state(self, *, bootstrap_if_ready: bool = True) -> DesktopRuntimeState:
        settings = self.load_settings()
        resolution = resolve_effective_source_root(self.layout, settings=settings, environ=self.environ)
        setup_required = setup_required_for_desktop(settings, resolution)
        source_root = str(resolution.get("source_root", "")).strip()

        if bootstrap_if_ready and not setup_required and source_root:
            self.logger.info(
                "Desktop bootstrap: source=%s reason=%s mode=%s",
                source_root,
                resolution.get("reason", ""),
                settings.get("source_mode", SOURCE_MODE_UNSET),
            )
            ensure_local_db_initialized(self.layout, self.logger, source_root_override=Path(source_root))

        return DesktopRuntimeState(
            layout=self.layout,
            settings=settings,
            source_root=source_root,
            source_reason=str(resolution.get("reason", "")).strip(),
            source_mode=str(settings.get("source_mode", SOURCE_MODE_UNSET)).strip().lower() or SOURCE_MODE_UNSET,
            source_exists=bool(Path(source_root).exists() and Path(source_root).is_dir()) if source_root else False,
            source_is_unc=bool(str(resolution.get("is_unc", False)).lower() == "true" or resolution.get("is_unc", False)),
            source_file_count=count_spreadsheet_files(source_root),
            db_path=str(self.layout["db_path"]),
            db_exists=self.layout["db_path"].exists(),
            setup_required=setup_required,
            settings_path=str(settings.get("config_path", "")),
            last_index=dict(settings.get("last_index") or {}),
        )

    # --- NEW: persist user-selected real source folder before indexing ---
    def configure_source_folder(self, source_root: str) -> DesktopRuntimeState:
        normalized = get_source_root(source_root)
        if not os.path.isdir(normalized):
            raise FileNotFoundError(f"Pasta de fonte nao encontrada: {normalized}")
        self.save_settings(
            {
                "source_mode": SOURCE_MODE_CONFIGURED,
                "source_root": normalized,
                "first_run_completed": True,
            }
        )
        return self.load_state(bootstrap_if_ready=False)

    # --- NEW: explicit local-inbox mode instead of accidental fallback ---
    def activate_local_inbox_mode(self) -> DesktopRuntimeState:
        self.save_settings(
            {
                "source_mode": SOURCE_MODE_LOCAL_INBOX,
                "source_root": "",
                "first_run_completed": True,
            }
        )
        return self.load_state(bootstrap_if_ready=False)

    # --- NEW: persist indexing outcome for later launches and diagnostics ---
    def _persist_index_result(
        self,
        *,
        source_mode: str,
        source_root: str,
        status: str,
        error: str = "",
        source_files: int = 0,
    ) -> None:
        settings = self.load_settings()
        settings["last_index"] = {
            "status": str(status),
            "error": str(error or ""),
            "db_path": str(self.layout["db_path"]),
            "source_root": str(source_root),
            "source_mode": str(source_mode),
            "source_file_count": int(source_files),
            "indexed_at": dt.datetime.now().isoformat(timespec="seconds"),
        }
        save_packaged_settings(settings, root=self.layout["app_root"])

    # --- NEW: installed-app indexing entrypoint reused by setup and maintenance actions ---
    def reindex_current_source(self) -> DesktopRuntimeState:
        state = self.load_state(bootstrap_if_ready=False)
        if state.setup_required:
            raise ValueError("Configure primeiro a pasta real das planilhas antes de indexar.")

        source_root = state.source_root
        source_mode = state.source_mode or SOURCE_MODE_UNSET
        result = reindex_local_database(self.layout, self.logger, source_root_override=Path(source_root))
        status = str(result.get("status", "")).strip()
        source_files = int(result.get("source_files", 0) or 0)

        if status == "indexed":
            self._persist_index_result(
                source_mode=source_mode,
                source_root=source_root,
                status="ok",
                source_files=source_files,
            )
            return self.load_state(bootstrap_if_ready=False)

        if status == "no_source_files":
            self._persist_index_result(
                source_mode=source_mode,
                source_root=source_root,
                status="no_source_files",
                source_files=source_files,
            )
            raise ValueError(f"Nenhum arquivo de planilha foi encontrado em: {source_root}")

        self._persist_index_result(
            source_mode=source_mode,
            source_root=source_root,
            status="error",
            error=f"status={status}",
            source_files=source_files,
        )
        raise RuntimeError(f"Falha ao atualizar banco local. status={status}")
