from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .identity import IdentityClaims


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TENANT_POLICY_FILE = ROOT / "config" / "andy_bi_tenant_policy.example.json"

ACTION_TO_PERMISSION = {
    "query": "can_query",
    "view_dashboard": "can_view_dashboard",
    "export": "can_export",
    "manage_sources": "can_manage_sources",
    "view_audit": "can_view_audit",
    "support_bundle": "can_run_support_bundle",
}


@dataclass(frozen=True)
class AccessRequest:
    action: str
    tenant_id: str | None = None
    state: str | None = None
    source_root: str | None = None


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    reason: str
    action: str
    tenant_id: str | None = None
    state: str | None = None
    matched_roles: tuple[str, ...] = field(default_factory=tuple)
    audit_required: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "action": self.action,
            "tenant_id": self.tenant_id,
            "state": self.state,
            "matched_roles": list(self.matched_roles),
            "audit_required": self.audit_required,
        }


class TenantPolicyResolver:
    """Small RBAC/ABAC resolver for pre-corporate BI tests."""

    def __init__(self, policy: dict[str, Any]) -> None:
        self.policy = policy

    @classmethod
    def from_file(cls, path: str | Path = DEFAULT_TENANT_POLICY_FILE) -> "TenantPolicyResolver":
        policy_path = Path(path)
        data = json.loads(policy_path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError("tenant_policy_json_root_must_be_object")
        return cls(data)

    def evaluate(self, claims: IdentityClaims | None, request: AccessRequest) -> AccessDecision:
        if claims is None:
            return self._deny(request, "identity_required")
        if self.policy.get("default_decision") != "deny":
            return self._deny(request, "policy_must_default_to_deny")
        permission = ACTION_TO_PERMISSION.get(request.action)
        if permission is None:
            return self._deny(request, "unknown_action")

        roles = self.policy.get("roles", {})
        if not isinstance(roles, dict):
            return self._deny(request, "invalid_roles_policy")
        matching_roles = tuple(role for role in claims.roles if isinstance(roles.get(role), dict))
        if not matching_roles:
            return self._deny(request, "no_matching_role")
        permission_roles = tuple(role for role in matching_roles if roles[role].get(permission) is True)
        if not permission_roles:
            return self._deny(request, f"permission_denied:{permission}")

        tenant = self._find_tenant(request.tenant_id)
        if request.tenant_id and tenant is None:
            return self._deny(request, "tenant_not_found")
        if request.tenant_id and not self._scope_contains(claims.distributor_scope, request.tenant_id):
            return self._deny(request, "tenant_outside_identity_scope")
        if request.state and not self._scope_contains(claims.state_scope, request.state):
            return self._deny(request, "state_outside_identity_scope")
        if tenant is not None:
            allowed_roles = tuple(str(role) for role in tenant.get("allowed_roles", []) if str(role))
            if allowed_roles and not any(role in allowed_roles for role in permission_roles):
                return self._deny(request, "role_not_allowed_for_tenant")
            tenant_state = str(tenant.get("state", "")).strip()
            if request.state and tenant_state and tenant_state != request.state:
                return self._deny(request, "tenant_state_mismatch")
            if request.source_root and not self._source_allowed(claims, tenant, request.source_root):
                return self._deny(request, "source_outside_scope")

        return AccessDecision(
            allowed=True,
            reason="allowed_by_identity_scope_and_role",
            action=request.action,
            tenant_id=request.tenant_id,
            state=request.state,
            matched_roles=permission_roles,
            audit_required=True,
        )

    def _find_tenant(self, tenant_id: str | None) -> dict[str, Any] | None:
        if not tenant_id:
            return None
        tenants = self.policy.get("tenants", [])
        if not isinstance(tenants, list):
            return None
        for tenant in tenants:
            if isinstance(tenant, dict) and str(tenant.get("tenant_id", "")).strip() == tenant_id:
                return tenant
        return None

    @staticmethod
    def _scope_contains(scope: tuple[str, ...], value: str) -> bool:
        return "*" in scope or value in scope

    @staticmethod
    def _source_allowed(claims: IdentityClaims, tenant: dict[str, Any], source_root: str) -> bool:
        if "*" in claims.source_scope:
            return True
        tenant_sources = tuple(str(item) for item in tenant.get("source_roots", []) if str(item))
        if source_root in claims.source_scope:
            return True
        return source_root in tenant_sources and (not claims.source_scope or source_root in claims.source_scope)

    @staticmethod
    def _deny(request: AccessRequest, reason: str) -> AccessDecision:
        return AccessDecision(
            allowed=False,
            reason=reason,
            action=request.action,
            tenant_id=request.tenant_id,
            state=request.state,
            matched_roles=(),
            audit_required=True,
        )
