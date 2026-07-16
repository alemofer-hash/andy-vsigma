from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .schema_version import ANDY_BI_DATASET_VERSION, ANDY_BI_SCHEMA_VERSION


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_lote(files: Mapping[str, str | Path]) -> str:
    h = hashlib.sha256()
    for name in sorted(files):
        path = Path(files[name])
        h.update(name.encode("utf-8"))
        h.update(file_sha256(path).encode("ascii"))
    return h.hexdigest()


def build_publish_manifest(
    *,
    lote_id: str,
    files: Mapping[str, str | Path],
    row_counts: Mapping[str, int],
    source_fingerprint: str,
    source_period_start: str,
    source_period_end: str,
    validation_status: str,
    source_cadence_summary: Mapping[str, Any],
    quality_flags: Mapping[str, int],
    audit_summary: Mapping[str, Any],
    created_by_runtime: str = "andy_bi_dataset_builder",
    andy_engine_version: str = "unknown",
) -> dict[str, Any]:
    file_entries = {
        table: {
            "path": Path(path).name,
            "sha256": file_sha256(path),
        }
        for table, path in sorted(files.items())
    }
    return {
        "dataset_version": ANDY_BI_DATASET_VERSION,
        "schema_version": ANDY_BI_SCHEMA_VERSION,
        "build_timestamp": now_utc(),
        "source_fingerprint": source_fingerprint,
        "source_period_start": source_period_start,
        "source_period_end": source_period_end,
        "lote_id": lote_id,
        "hash_lote": hash_lote(files),
        "created_by_runtime": created_by_runtime,
        "andy_engine_version": andy_engine_version,
        "validation_status": validation_status,
        "source_cadence_summary": dict(source_cadence_summary),
        "row_counts": dict(row_counts),
        "quality_flags": dict(quality_flags),
        "audit_summary": dict(audit_summary),
        "files": file_entries,
        "safety_boundary": {
            "published_to_corporate_bi": False,
            "contains_credentials": False,
            "contains_real_endpoint_values": False,
            "source_root_written": False,
        },
    }


def write_manifest(path: str | Path, manifest: Mapping[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dict(manifest), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def load_manifest(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("andy_bi_publish_manifest_must_be_object")
    return payload
