from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


PACKAGED_ROLLBACK_MANIFEST_FILENAME = "ROLLBACK_MANIFEST.json"
ROLLBACK_MANIFEST_VERSION = 1
ROLLBACK_STATE_VERSION = 1
DEFAULT_LOCAL_HOT_FALLBACK_LIMIT = 1
DEFAULT_LOCAL_APP_ROLLBACK_MODE = "one_hot_copy"
DEFAULT_LOCAL_STATE_ROLLBACK_MODE = "preserve_only"
DEFAULT_REMOTE_VAULT_MODE = "artifact_manifest_registry"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _payload_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relpath = str(path.relative_to(root)).replace("/", "\\")
        stat = path.stat()
        entries.append(
            {
                "relpath": relpath,
                "size_bytes": int(stat.st_size),
                "sha256": sha256_file(path),
            }
        )
    return entries


def default_rollback_policy() -> dict[str, Any]:
    return {
        "architecture": "selective_singularity_v1",
        "local_hot_fallback_limit": int(DEFAULT_LOCAL_HOT_FALLBACK_LIMIT),
        "local_app_rollback_mode": str(DEFAULT_LOCAL_APP_ROLLBACK_MODE),
        "local_state_rollback_mode": str(DEFAULT_LOCAL_STATE_ROLLBACK_MODE),
        "remote_rehydration_ready": True,
        "remote_vault_mode": str(DEFAULT_REMOTE_VAULT_MODE),
    }


def build_packaged_rollback_manifest(
    *,
    dist_root: Path,
    version: str,
    profile: str,
    app_name: str,
    app_exe_name: str,
    artifact_relpath: str,
    built_at_utc: str,
    workspace_schema_version: int = 1,
    catalog_schema_version: int = 1,
) -> dict[str, Any]:
    root = dist_root.resolve()
    entries = _payload_entries(root)
    total_size = int(sum(int(item["size_bytes"]) for item in entries))
    manifest_path = (root / PACKAGED_ROLLBACK_MANIFEST_FILENAME).resolve()

    return {
        "manifest_version": int(ROLLBACK_MANIFEST_VERSION),
        "generated_at_utc": str(built_at_utc or dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")),
        "app_name": str(app_name),
        "release": {
            "version": str(version).strip(),
            "profile": str(profile).strip(),
            "exe_name": str(app_exe_name).strip(),
            "artifact_relpath": str(artifact_relpath).strip(),
            "manifest_name": PACKAGED_ROLLBACK_MANIFEST_FILENAME,
            "manifest_relpath": str(manifest_path.relative_to(root)).replace("/", "\\"),
        },
        "compatibility": {
            "workspace_schema_version": int(workspace_schema_version),
            "catalog_schema_version": int(catalog_schema_version),
            "state_rollback_mode": str(DEFAULT_LOCAL_STATE_ROLLBACK_MODE),
            "schema_guard_mode": "binary_with_catalog_guard",
        },
        "policy": default_rollback_policy(),
        "payload": {
            "root_dirname": str(root.name),
            "file_count": int(len(entries)),
            "total_size_bytes": total_size,
        },
        "files": entries,
    }


def write_packaged_rollback_manifest(
    *,
    dist_root: Path,
    version: str,
    profile: str,
    app_name: str,
    app_exe_name: str,
    artifact_relpath: str,
    built_at_utc: str,
    workspace_schema_version: int = 1,
    catalog_schema_version: int = 1,
) -> Path:
    root = dist_root.resolve()
    manifest_path = (root / PACKAGED_ROLLBACK_MANIFEST_FILENAME).resolve()
    payload = build_packaged_rollback_manifest(
        dist_root=root,
        version=version,
        profile=profile,
        app_name=app_name,
        app_exe_name=app_exe_name,
        artifact_relpath=artifact_relpath,
        built_at_utc=built_at_utc,
        workspace_schema_version=workspace_schema_version,
        catalog_schema_version=catalog_schema_version,
    )
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return manifest_path


def load_packaged_rollback_manifest(path: Path) -> dict[str, Any]:
    target = path.resolve()
    if not target.exists():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def make_release_key(*, app_name: str, version: str, profile: str) -> str:
    return "::".join(
        [
            str(app_name or "").strip(),
            str(version or "").strip(),
            str(profile or "").strip(),
        ]
    )


def summarize_hot_fallback(*, path: str, version: str, exists: bool) -> dict[str, Any]:
    text = str(path or "").strip()
    return {
        "kind": "full_install_copy" if text else "",
        "path": text,
        "version": str(version or "").strip(),
        "exists": bool(exists and text),
    }


def normalize_remote_vault(payload: Mapping[str, Any] | None, *, manifest_path: str, release_key: str) -> dict[str, Any]:
    raw = dict(payload or {})
    return {
        "enabled": bool(raw.get("enabled", True)),
        "mode": str(raw.get("mode", "")).strip() or DEFAULT_REMOTE_VAULT_MODE,
        "manifest_ref": str(raw.get("manifest_ref", "")).strip() or str(manifest_path or "").strip(),
        "release_key": str(raw.get("release_key", "")).strip() or str(release_key or "").strip(),
        "remote_required_for_cold_rollback": bool(raw.get("remote_required_for_cold_rollback", True)),
    }
