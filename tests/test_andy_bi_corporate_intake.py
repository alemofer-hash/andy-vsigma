from __future__ import annotations

import json
from pathlib import Path

from andy_bi.https_security import redacted_url_summary, validate_https_security_config


ROOT = Path(__file__).resolve().parents[1]


def _load_example() -> dict:
    return json.loads((ROOT / "config" / "andy_bi_corporate_intake.example.json").read_text(encoding="utf-8"))


def test_corporate_intake_example_is_https_ready_and_redacted() -> None:
    report = validate_https_security_config(_load_example())

    assert report.status == "https_security_ready"
    assert not report.findings
    assert report.safety_boundary["connects_to_network"] is False
    assert report.safety_boundary["prints_raw_urls"] is False
    assert all("host_hash" in endpoint for endpoint in report.endpoints)


def test_plain_http_is_rejected_except_localhost_redirect() -> None:
    config = _load_example()
    config["identity_provider"]["authority_url"] = "http://idp.example.invalid/tenant"
    config["identity_provider"]["redirect_uri"] = "http://localhost:7777/callback"

    report = validate_https_security_config(config)

    assert report.status == "blocked"
    assert any(finding.code == "https_required" for finding in report.findings)
    assert not any(finding.code == "only_localhost_http_redirect_allowed" for finding in report.findings)


def test_non_localhost_http_redirect_is_rejected() -> None:
    config = _load_example()
    config["identity_provider"]["redirect_uri"] = "http://workstation.example.invalid/callback"

    report = validate_https_security_config(config)

    assert report.status == "blocked"
    assert any(finding.code == "only_localhost_http_redirect_allowed" for finding in report.findings)


def test_ldap_requires_ldaps() -> None:
    config = _load_example()
    config["ldap"]["server_url"] = "ldap://ldap.example.invalid"

    report = validate_https_security_config(config)

    assert report.status == "blocked"
    assert any(finding.code == "ldaps_required" for finding in report.findings)


def test_tls_verification_and_secret_values_are_required() -> None:
    config = _load_example()
    config["https_security"]["verify_tls_certificates"] = False
    config["https_security"]["allow_self_signed_certificates"] = True
    config["identity_provider"]["client_secret"] = "do-not-store-this"

    report = validate_https_security_config(config)
    codes = {finding.code for finding in report.findings}

    assert report.status == "blocked"
    assert "tls_certificate_verification_required" in codes
    assert "self_signed_certificates_not_allowed" in codes
    assert "secret_like_value_not_allowed" in codes


def test_redacted_url_summary_never_returns_raw_host() -> None:
    summary = redacted_url_summary("https://private-idp.example.invalid/path/to/metadata")

    assert summary["scheme"] == "https"
    assert summary["host_redacted"] is True
    assert summary["host_hash"]
    assert "private-idp" not in json.dumps(summary)


def test_corporate_intake_checker_reports_ready() -> None:
    import scripts.check_andy_bi_corporate_intake as checker

    report = checker.build_report()

    assert report["status"] == "corporate_intake_https_ready"
    assert report["checks"]["https_security_ready"] is True
    assert report["safety_boundary"]["connects_to_network"] is False
    assert report["safety_boundary"]["prints_raw_urls"] is False
