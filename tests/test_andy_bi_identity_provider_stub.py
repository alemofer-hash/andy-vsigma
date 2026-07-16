from __future__ import annotations

import json
from pathlib import Path

from andy_bi.enforcement import evaluate_boundary_policy
from andy_bi.providers import (
    CORPORATE_PROVIDER_TYPES,
    CorporateIdentityAdapterStub,
    MockClaimsIdentityProvider,
    load_provider_template,
    resolve_identity_for_policy,
)


ROOT = Path(__file__).resolve().parents[1]


def _enabled_mock_file(tmp_path: Path) -> Path:
    source = ROOT / "config" / "andy_bi_mock_claims.example.json"
    target = tmp_path / "andy_bi_mock_claims.private.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    data["mock_enabled"] = True
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def test_provider_template_keeps_corporate_providers_as_stub_only() -> None:
    template = load_provider_template(ROOT / "config" / "andy_bi_identity_provider.example.json")

    assert template["default_provider"] == "mock_claims"
    assert template["security_rules"]["store_user_password"] is False
    assert template["security_rules"]["store_client_secret"] is False
    assert template["security_rules"]["network_calls_allowed_in_stub"] is False
    for provider_type in CORPORATE_PROVIDER_TYPES:
        assert template["providers"][provider_type]["enabled"] is False
        assert template["providers"][provider_type]["stub_only"] is True


def test_mock_claims_provider_resolves_fictitious_claims(tmp_path: Path) -> None:
    provider = MockClaimsIdentityProvider(config_path=_enabled_mock_file(tmp_path), enabled=True)

    result = provider.resolve("mock_engineer_rs")

    assert result.status == "resolved"
    assert result.provider_type == "mock_claims"
    assert result.claims is not None
    assert result.claims.subject == "mock-user-engineer-rs"
    assert result.safety["connects_to_corporate_network"] is False
    assert result.safety["stores_passwords"] is False


def test_corporate_identity_provider_stub_blocks_without_network() -> None:
    provider = CorporateIdentityAdapterStub("oidc", config_path=ROOT / "config" / "andy_bi_identity_provider.example.json", enabled=True)

    result = provider.resolve("any-user")

    assert result.status == "blocked"
    assert result.provider_type == "oidc"
    assert result.reason == "oidc_corporate_identity_provider_stub_not_implemented"
    assert result.safety["connects_to_corporate_network"] is False
    assert result.safety["stores_passwords"] is False
    assert result.safety["uses_real_identity_provider"] is False


def test_resolve_identity_for_policy_routes_mock_and_corporate_stub(tmp_path: Path) -> None:
    mock = resolve_identity_for_policy(
        {
            "identity_provider": "mock_claims",
            "identity_key": "mock_engineer_rs",
            "mock_claims_file": str(_enabled_mock_file(tmp_path)),
        }
    )
    oidc = resolve_identity_for_policy(
        {
            "identity_provider": "oidc",
            "identity_key": "mock_engineer_rs",
            "identity_provider_config": str(ROOT / "config" / "andy_bi_identity_provider.example.json"),
            "provider_enabled": True,
        }
    )

    assert mock.status == "resolved"
    assert oidc.status == "blocked"
    assert oidc.reason == "oidc_corporate_identity_provider_stub_not_implemented"


def test_enforcement_blocks_corporate_provider_stub_before_query() -> None:
    result = evaluate_boundary_policy(
        "query.page",
        {
            "db_path": "missing_should_not_be_opened.duckdb",
            "bi_policy": {
                "enabled": True,
                "identity_provider": "oidc",
                "identity_key": "mock_engineer_rs",
                "identity_provider_config": str(ROOT / "config" / "andy_bi_identity_provider.example.json"),
                "provider_enabled": True,
                "tenant_policy_file": str(ROOT / "config" / "andy_bi_tenant_policy.example.json"),
            },
            "bi_scope": {
                "tenant_id": "DISTRIBUTOR_RS_PLACEHOLDER",
                "state": "RS",
                "source_root": "${ANDY_BI_RS_SOURCE_ROOT}",
            },
        },
    )

    assert result.status == "blocked"
    assert result.reason == "identity_resolution_blocked:oidc_corporate_identity_provider_stub_not_implemented"
    assert result.safety["connects_to_corporate_network"] is False


def test_identity_provider_stub_checker_reports_ready() -> None:
    import scripts.check_andy_bi_identity_provider_stub as checker

    report = checker.build_report()

    assert report["status"] == "corporate_identity_adapter_stub_ready"
    assert report["checks"]["corporate_providers_are_stub_only"] is True
    assert report["checks"]["enforcement_blocks_corporate_stub"] is True
    assert report["safety_boundary"]["connects_to_corporate_network"] is False
