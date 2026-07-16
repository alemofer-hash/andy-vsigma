from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _private_config(tmp_path: Path) -> Path:
    source = ROOT / "config" / "andy_bi_corporate_intake.example.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    target = tmp_path / "andy_bi_corporate_intake.private.json"
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def test_corporate_config_review_waits_without_private_config() -> None:
    import scripts.check_andy_bi_corporate_config_review as checker

    report = checker.build_report(ROOT / "config" / "missing_private_config_for_review_test.json")

    assert report["status"] == "waiting_for_private_config"
    assert report["review_decision"] == "HOLD_WAITING_FOR_CORPORATE_IT_INPUT"
    assert report["checks"]["readiness_gate_ready"] is True
    assert report["checks"]["private_config_present"] is False
    assert report["review_scope"]["connects_to_network"] is False
    assert report["review_scope"]["activates_real_identity_provider"] is False


def test_corporate_config_review_accepts_synthetic_private_config_and_redacts(tmp_path: Path) -> None:
    import scripts.check_andy_bi_corporate_config_review as checker

    report = checker.build_report(_private_config(tmp_path))
    encoded = json.dumps(report, ensure_ascii=False)

    assert report["status"] == "ready_for_human_security_review"
    assert report["review_decision"] == "ALLOW_REDACTED_HUMAN_REVIEW_BEFORE_PROVIDER_IMPLEMENTATION"
    assert report["checks"]["private_config_dry_run_ready"] is True
    assert report["checks"]["no_network_calls"] is True
    assert "idp.example.invalid" not in encoded
    assert "audit.example.invalid" not in encoded
    assert "catalog.example.invalid" not in encoded
