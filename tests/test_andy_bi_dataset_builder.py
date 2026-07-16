from __future__ import annotations

from pathlib import Path

from andy_bi.dataset_builder import build_andy_bi_dataset
from andy_bi.publish_manifest import load_manifest


def test_dataset_builder_emits_governed_synthetic_package(tmp_path: Path) -> None:
    result = build_andy_bi_dataset(out_dir=tmp_path, fmt="both", synthetic=True, lote_id="unit_lote")

    assert result.validation_status == "valid"
    assert result.synthetic is True
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "schema.json").exists()
    assert (tmp_path / "fact_power_flow.parquet").exists()
    assert (tmp_path / "fact_power_flow.csv").exists()
    manifest = load_manifest(tmp_path / "manifest.json")
    assert manifest["safety_boundary"]["published_to_corporate_bi"] is False
    assert manifest["audit_summary"]["synthetic"] is True


def test_dataset_builder_requires_explicit_allow_for_local_duckdb(tmp_path: Path) -> None:
    db = tmp_path / "local.duckdb"
    db.write_bytes(b"not-a-real-db")

    try:
        build_andy_bi_dataset(out_dir=tmp_path / "out", source_db=db)
    except ValueError as exc:
        assert str(exc) == "source_db_requires_allow_local_data"
    else:  # pragma: no cover - defensive failure path.
        raise AssertionError("source_db should require explicit allow_local_data")
