from __future__ import annotations

from pathlib import Path

from andy_bi.publish_manifest import build_publish_manifest, load_manifest, write_manifest


def test_publish_manifest_contains_lote_hash_and_safety_boundary(tmp_path: Path) -> None:
    data_file = tmp_path / "fact.csv"
    data_file.write_text("a\n1\n", encoding="utf-8")

    manifest = build_publish_manifest(
        lote_id="lote_manifest_test",
        files={"fact:test": data_file},
        row_counts={"fact": 1},
        source_fingerprint="synthetic-demo",
        source_period_start="2026-01-01T00:00:00",
        source_period_end="2026-01-01T00:15:00",
        validation_status="valid",
        source_cadence_summary={"15min": 1},
        quality_flags={"OK": 1},
        audit_summary={"synthetic": True},
    )
    path = write_manifest(tmp_path / "manifest.json", manifest)
    loaded = load_manifest(path)

    assert loaded["lote_id"] == "lote_manifest_test"
    assert loaded["hash_lote"]
    assert loaded["safety_boundary"]["published_to_corporate_bi"] is False
