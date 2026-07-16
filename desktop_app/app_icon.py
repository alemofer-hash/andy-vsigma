from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

from PySide6.QtGui import QIcon

from runtime_paths import get_bundle_path, get_project_root


APP_ICON_RELATIVE_PATH = Path("assets") / "icons" / "andy_vsigma.ico"


def _candidate_icon_paths() -> list[Path]:
    candidates: list[Path] = []
    seen: set[str] = set()

    for root in (get_bundle_path(), get_project_root()):
        candidate = (root / APP_ICON_RELATIVE_PATH).resolve()
        normalized = str(candidate).lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        candidates.append(candidate)

    if bool(getattr(sys, "frozen", False)):
        exe_candidate = (Path(sys.executable).resolve().parent / APP_ICON_RELATIVE_PATH).resolve()
        normalized = str(exe_candidate).lower()
        if normalized not in seen:
            candidates.append(exe_candidate)

    return candidates


@lru_cache(maxsize=1)
def resolve_app_icon_path() -> Path:
    candidates = _candidate_icon_paths()
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


@lru_cache(maxsize=1)
def load_app_icon() -> QIcon:
    for candidate in _candidate_icon_paths():
        if not candidate.exists():
            continue
        icon = QIcon(str(candidate))
        if not icon.isNull():
            return icon
    return QIcon()


def apply_app_icon_to_application(app: object) -> QIcon:
    icon = load_app_icon()
    if not icon.isNull() and hasattr(app, "setWindowIcon"):
        app.setWindowIcon(icon)
    return icon


def apply_app_icon_to_window(window: object) -> QIcon:
    icon = load_app_icon()
    if not icon.isNull() and hasattr(window, "setWindowIcon"):
        window.setWindowIcon(icon)
    return icon
