from __future__ import annotations

import json
from pathlib import Path

from andy_bi.dataset_builder import build_andy_bi_dataset
from andy_bi.pilot_report import build_pilot_report, pilot_pages, validate_pilot_inputs
from andy_bi.publish_manifest import load_manifest
from andy_bi.semantic_dataset import load_dataset_frames


def test_pilot_report_builds_publicable_synthetic_html(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    report = tmp_path / "report"
    build_andy_bi_dataset(out_dir=dataset, fmt="both", synthetic=True, lote_id="pilot_unit")

    result = build_pilot_report(dataset_dir=dataset, out_dir=report)

    assert result.status == "passed"
    assert result.synthetic is True
    assert result.html_path.exists()
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["published_to_corporate_bi"] is False
    assert manifest["contains_real_data"] is False
    assert manifest["safe_for_publication_review"] is True
    assert "Cockpit Executivo ANDY" in result.html_path.read_text(encoding="utf-8")


def test_pilot_report_pages_cover_required_spec() -> None:
    pages = pilot_pages()

    assert set(pages) == {
        "Cockpit Executivo ANDY",
        "Catalogo de Medicoes",
        "Patamar e Carga",
        "Fluxo P/Q e Inversao",
        "Qualidade e Auditoria",
        "Paridade ANDY Desktop",
    }


def test_pilot_validation_requires_synthetic_manifest(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    build_andy_bi_dataset(out_dir=dataset, fmt="both", synthetic=True, lote_id="pilot_unit")
    frames = load_dataset_frames(dataset)
    manifest = load_manifest(dataset / "manifest.json")
    manifest["audit_summary"]["synthetic"] = False

    findings = validate_pilot_inputs(frames, manifest, require_synthetic=True)

    assert "pilot_requires_synthetic_dataset" in findings
