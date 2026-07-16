from __future__ import annotations

import json
import shutil
from pathlib import Path

from andy_bi.identity import IdentityClaims, MockIdentityResolver
from andy_bi.policy import AccessRequest, TenantPolicyResolver


ROOT = Path(__file__).resolve().parents[1]


def _enabled_mock_file(tmp_path: Path) -> Path:
    source = ROOT / "config" / "andy_bi_mock_claims.example.json"
    target = tmp_path / "andy_bi_mock_claims.private.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    data["mock_enabled"] = True
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def test_mock_identity_resolver_is_disabled_by_default() -> None:
    resolution = MockIdentityResolver(config_path=ROOT / "config" / "andy_bi_mock_claims.example.json").resolve()

    assert resolution.status == "disabled"
    assert resolution.claims is None
    assert resolution.safety["network_calls"] is False
    assert resolution.safety["password_storage"] is False


def test_mock_identity_requires_config_to_enable_mock(tmp_path: Path) -> None:
    disabled_config = tmp_path / "claims.json"
    shutil.copyfile(ROOT / "config" / "andy_bi_mock_claims.example.json", disabled_config)

    resolution = MockIdentityResolver(enabled=True, config_path=disabled_config).resolve("mock_engineer_rs")

    assert resolution.status == "blocked"
    assert resolution.reason == "mock_config_must_set_mock_enabled_true"


def test_enabled_mock_identity_resolves_fictitious_claims(tmp_path: Path) -> None:
    resolution = MockIdentityResolver(enabled=True, config_path=_enabled_mock_file(tmp_path)).resolve("mock_engineer_rs")

    assert resolution.status == "resolved"
    assert isinstance(resolution.claims, IdentityClaims)
    assert resolution.claims.subject == "mock-user-engineer-rs"
    assert resolution.claims.roles == ("engineer",)
    assert resolution.claims.distributor_scope == ("DISTRIBUTOR_RS_PLACEHOLDER",)
    assert resolution.claims.state_scope == ("RS",)


def test_tenant_policy_allows_and_denies_by_scope_and_role(tmp_path: Path) -> None:
    resolver = MockIdentityResolver(enabled=True, config_path=_enabled_mock_file(tmp_path))
    engineer = resolver.resolve("mock_engineer_rs").claims
    viewer = resolver.resolve("mock_viewer_pa").claims
    policy = TenantPolicyResolver.from_file(ROOT / "config" / "andy_bi_tenant_policy.example.json")

    engineer_query = policy.evaluate(
        engineer,
        AccessRequest("query", tenant_id="DISTRIBUTOR_RS_PLACEHOLDER", state="RS", source_root="${ANDY_BI_RS_SOURCE_ROOT}"),
    )
    engineer_export = policy.evaluate(
        engineer,
        AccessRequest("export", tenant_id="DISTRIBUTOR_RS_PLACEHOLDER", state="RS", source_root="${ANDY_BI_RS_SOURCE_ROOT}"),
    )
    engineer_wrong_tenant = policy.evaluate(
        engineer,
        AccessRequest("query", tenant_id="DISTRIBUTOR_PA_PLACEHOLDER", state="PA", source_root="${ANDY_BI_PA_SOURCE_ROOT}"),
    )
    viewer_export = policy.evaluate(
        viewer,
        AccessRequest("export", tenant_id="DISTRIBUTOR_PA_PLACEHOLDER", state="PA", source_root="${ANDY_BI_PA_SOURCE_ROOT}"),
    )

    assert engineer_query.allowed is True
    assert engineer_export.allowed is True
    assert engineer_wrong_tenant.allowed is False
    assert engineer_wrong_tenant.reason == "tenant_outside_identity_scope"
    assert viewer_export.allowed is False
    assert viewer_export.reason == "permission_denied:can_export"


def test_identity_mock_checker_reports_ready() -> None:
    import scripts.check_andy_bi_identity_mock as checker

    report = checker.build_report()

    assert report["status"] == "identity_contract_mock_ready"
    assert report["checks"]["mock_claims_disabled_by_default"] is True
    assert report["checks"]["engineer_query_allowed_in_scope"] is True
    assert report["checks"]["engineer_query_denied_outside_scope"] is True
    assert report["safety_boundary"]["connects_to_corporate_network"] is False
    assert report["safety_boundary"]["stores_passwords"] is False
