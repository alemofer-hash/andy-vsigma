from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _private_config(tmp_path: Path, **updates) -> Path:
    source = ROOT / "config" / "andy_bi_corporate_intake.example.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    for dotted_key, value in updates.items():
        current = data
        parts = dotted_key.split("__")
        for part in parts[:-1]:
            current = current[part]
        current[parts[-1]] = value
    target = tmp_path / "andy_bi_corporate_intake.private.json"
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def test_private_config_dry_run_waits_when_default_private_config_is_missing() -> None:
    import scripts.check_andy_bi_private_config_dry_run as checker

    report = checker.build_report(ROOT / "config" / "missing_private_config_for_test.json")

    assert report["status"] == "waiting_for_private_config"
    assert report["checks"]["private_config_exists"] is False
    assert report["safety_boundary"]["connects_to_network"] is False


def test_private_config_dry_run_accepts_valid_private_config_and_redacts(tmp_path: Path) -> None:
    import scripts.check_andy_bi_private_config_dry_run as checker

    config_path = _private_config(tmp_path)
    report = checker.build_report(config_path)
    encoded = json.dumps(report, ensure_ascii=False)

    assert report["status"] == "private_config_dry_run_ready"
    assert report["checks"]["private_config_not_tracked"] is True
    assert report["checks"]["https_security_ready"] is True
    assert report["checks"]["report_redacts_endpoints"] is True
    assert report["config_fingerprint_sha256"]
    assert "idp.example.invalid" not in encoded
    assert "audit.example.invalid" not in encoded
    assert "catalog.example.invalid" not in encoded
    assert report["safety_boundary"]["uses_private_config_for_authentication"] is False


def test_private_config_dry_run_blocks_plain_http(tmp_path: Path) -> None:
    import scripts.check_andy_bi_private_config_dry_run as checker

    config_path = _private_config(tmp_path, identity_provider__authority_url="http://idp.example.invalid/tenant")
    report = checker.build_report(config_path)

    assert report["status"] == "blocked"
    assert "https_security_ready" in report["failures"]
    assert any(item["code"] == "https_required" for item in report["https_security"]["findings"])


def test_private_config_dry_run_blocks_secret_values(tmp_path: Path) -> None:
    import scripts.check_andy_bi_private_config_dry_run as checker

    config_path = _private_config(tmp_path, identity_provider__client_secret="do-not-store-this")
    report = checker.build_report(config_path)

    assert report["status"] == "blocked"
    assert any(item["code"] == "secret_like_value_not_allowed" for item in report["https_security"]["findings"])


def test_private_config_dry_run_blocks_relaxed_tls(tmp_path: Path) -> None:
    import scripts.check_andy_bi_private_config_dry_run as checker

    config_path = _private_config(
        tmp_path,
        https_security__verify_tls_certificates=False,
        https_security__allow_self_signed_certificates=True,
    )
    report = checker.build_report(config_path)
    codes = {item["code"] for item in report["https_security"]["findings"]}

    assert report["status"] == "blocked"
    assert "tls_certificate_verification_required" in codes
    assert "self_signed_certificates_not_allowed" in codes
