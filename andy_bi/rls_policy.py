from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .access_model import AccessEvaluation, AccessPrincipal, AccessScope
from .schema_version import ANDY_BI_RLS_POLICY_VERSION


def default_rls_policy() -> dict[str, Any]:
    return {
        "schema": ANDY_BI_RLS_POLICY_VERSION,
        "default_decision": "deny",
        "identity_source": "corporate_platform_or_mock_for_tests",
        "real_provider_enabled": False,
        "roles": {
            "viewer": {"can_view": True, "can_export": False, "can_admin_dataset": False},
            "engineer": {"can_view": True, "can_export": True, "can_admin_dataset": False},
            "auditor": {"can_view": True, "can_export": False, "can_view_audit": True},
            "admin_dataset": {"can_view": True, "can_export": True, "can_admin_dataset": True},
            "bi_owner": {"can_view": True, "can_export": True, "can_admin_dataset": True},
        },
        "scopes": [
            {
                "scope_id": "demo_rs_engineering",
                "distributor": "DEMO",
                "state": "RS",
                "source_id": "source_demo",
                "allowed_roles": ["viewer", "engineer", "auditor", "admin_dataset", "bi_owner"],
            }
        ],
    }


def load_rls_policy(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("rls_policy_root_must_be_object")
    return payload


def write_default_rls_policy(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(default_rls_policy(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def validate_rls_policy(policy: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    if policy.get("schema") != ANDY_BI_RLS_POLICY_VERSION:
        failures.append("schema_version_mismatch")
    if policy.get("default_decision") != "deny":
        failures.append("deny_by_default_required")
    if policy.get("real_provider_enabled") is not False:
        failures.append("real_provider_must_be_disabled_in_example")
    roles = policy.get("roles")
    if not isinstance(roles, Mapping) or not roles:
        failures.append("roles_required")
    scopes = policy.get("scopes")
    if not isinstance(scopes, list):
        failures.append("scopes_must_be_list")
    return failures


def evaluate_rls(
    claims: Mapping[str, Any] | AccessPrincipal | None,
    scope: AccessScope,
    *,
    action: str = "view",
    policy: Mapping[str, Any] | None = None,
) -> AccessEvaluation:
    active_policy = dict(policy or default_rls_policy())
    if active_policy.get("default_decision") != "deny":
        return _deny(claims, scope, "policy_not_deny_by_default")
    if claims is None:
        return _deny(claims, scope, "identity_required")
    principal = claims if isinstance(claims, AccessPrincipal) else AccessPrincipal.from_claims(claims)
    if not principal.subject:
        return AccessEvaluation(False, "subject_required", principal.subject, scope)
    matching_roles = [role for role in principal.roles if _role_allows(active_policy, role, action)]
    if not matching_roles:
        return AccessEvaluation(False, "role_denied", principal.subject, scope)
    matched_scope = _find_scope(active_policy, scope)
    if matched_scope is None:
        return AccessEvaluation(False, "scope_not_defined", principal.subject, scope)
    allowed_roles = {str(item) for item in matched_scope.get("allowed_roles", [])}
    if allowed_roles and not any(role in allowed_roles for role in matching_roles):
        return AccessEvaluation(False, "role_not_allowed_for_scope", principal.subject, scope)
    if scope.distributor and not _contains(principal.distributors, scope.distributor):
        return AccessEvaluation(False, "distributor_outside_claims", principal.subject, scope)
    if scope.state and not _contains(principal.states, scope.state):
        return AccessEvaluation(False, "state_outside_claims", principal.subject, scope)
    if scope.source_id and principal.sources and not _contains(principal.sources, scope.source_id):
        return AccessEvaluation(False, "source_outside_claims", principal.subject, scope)
    return AccessEvaluation(True, "allowed_by_rls_abac_policy", principal.subject, scope)


def _role_allows(policy: Mapping[str, Any], role: str, action: str) -> bool:
    role_rules = policy.get("roles", {}).get(role, {})
    if not isinstance(role_rules, Mapping):
        return False
    permission = {
        "view": "can_view",
        "export": "can_export",
        "admin_dataset": "can_admin_dataset",
        "view_audit": "can_view_audit",
    }.get(action, f"can_{action}")
    return role_rules.get(permission) is True


def _find_scope(policy: Mapping[str, Any], scope: AccessScope) -> Mapping[str, Any] | None:
    scopes = policy.get("scopes", [])
    if not isinstance(scopes, list):
        return None
    for item in scopes:
        if not isinstance(item, Mapping):
            continue
        if scope.distributor and item.get("distributor") != scope.distributor:
            continue
        if scope.state and item.get("state") != scope.state:
            continue
        if scope.source_id and item.get("source_id") != scope.source_id:
            continue
        return item
    return None


def _contains(scope: tuple[str, ...], value: str) -> bool:
    return "*" in scope or value in scope


def _deny(claims: Mapping[str, Any] | AccessPrincipal | None, scope: AccessScope, reason: str) -> AccessEvaluation:
    subject = claims.subject if isinstance(claims, AccessPrincipal) else str((claims or {}).get("subject", ""))
    return AccessEvaluation(False, reason, subject, scope)
