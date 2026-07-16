from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .identity import IdentityClaims
from .policy import AccessDecision, AccessRequest, TenantPolicyResolver
from .providers import resolve_identity_for_policy


TRUTHY = {"1", "true", "yes", "y", "on", "sim"}
FEATURE_FLAG = "ANDY_BI_POLICY_ENFORCEMENT_ENABLED"
MOCK_CLAIMS_FILE_ENV = "ANDY_BI_MOCK_CLAIMS_FILE"
TENANT_POLICY_FILE_ENV = "ANDY_BI_TENANT_POLICY_FILE"

DEFAULT_TENANT_POLICY_FILE = Path(__file__).resolve().parents[1] / "config" / "andy_bi_tenant_policy.example.json"

OPERATION_ACTIONS = {
    "query.overview": "query",
    "query.options": "query",
    "query.page": "query",
    "load_profile.analyze": "query",
    "export.audit": "export",
    "export.csv_long": "export",
    "export.csv_wide": "export",
    "export.xlsx_dashboard": "export",
}


class PolicyEnforcementDenied(ValueError):
    def __init__(self, result: "PolicyEnforcementResult") -> None:
        super().__init__(f"BI policy denied {result.operation}: {result.reason}")
        self.result = result


@dataclass(frozen=True)
class PolicyEnforcementResult:
    status: str
    operation: str
    action: str = ""
    reason: str = ""
    decision: AccessDecision | None = None
    claims_summary: dict[str, Any] | None = None
    enabled: bool = False
    enforcement_mode: str = "disabled"
    safety: dict[str, bool] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.status in {"disabled", "allowed", "not_applicable"}

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "operation": self.operation,
            "action": self.action,
            "reason": self.reason,
            "decision": self.decision.as_dict() if self.decision else None,
            "claims_summary": self.claims_summary,
            "enabled": self.enabled,
            "enforcement_mode": self.enforcement_mode,
            "safety": self.safety,
        }


def policy_enforcement_enabled(payload: Mapping[str, Any] | None = None) -> bool:
    policy_payload = _policy_payload(payload or {})
    if "enabled" in policy_payload:
        return _as_bool(policy_payload.get("enabled"))
    if "bi_policy_enforcement_enabled" in (payload or {}):
        return _as_bool((payload or {}).get("bi_policy_enforcement_enabled"))
    return os.environ.get(FEATURE_FLAG, "").strip().lower() in TRUTHY


def evaluate_boundary_policy(
    operation: str,
    payload: Mapping[str, Any],
    *,
    enabled: bool | None = None,
) -> PolicyEnforcementResult:
    action = OPERATION_ACTIONS.get(operation)
    safety = {
        "connects_to_corporate_network": False,
        "stores_passwords": False,
        "uses_real_identity_provider": False,
        "changes_analytical_engine": False,
    }
    if action is None:
        return PolicyEnforcementResult(
            status="not_applicable",
            operation=operation,
            reason="operation_not_subject_to_bi_policy",
            enabled=False,
            safety=safety,
        )
    is_enabled = policy_enforcement_enabled(payload) if enabled is None else bool(enabled)
    if not is_enabled:
        return PolicyEnforcementResult(
            status="disabled",
            operation=operation,
            action=action,
            reason="bi_policy_enforcement_disabled",
            enabled=False,
            enforcement_mode="disabled",
            safety=safety,
        )

    policy_payload = _policy_payload(payload)
    claims_resolution = _resolve_claims(policy_payload)
    if claims_resolution.status != "resolved" or claims_resolution.claims is None:
        return PolicyEnforcementResult(
            status="blocked",
            operation=operation,
            action=action,
            reason=f"identity_resolution_{claims_resolution.status}:{claims_resolution.reason}",
            claims_summary=claims_resolution.public_summary().get("claims"),
            enabled=True,
            enforcement_mode="mock_claims",
            safety=safety,
        )

    scope = _scope_payload(payload)
    missing_scope = [name for name in ("tenant_id", "state", "source_root") if not _optional_text(scope.get(name))]
    if missing_scope:
        return PolicyEnforcementResult(
            status="blocked",
            operation=operation,
            action=action,
            reason="bi_scope_required:" + ",".join(missing_scope),
            claims_summary=claims_resolution.claims.public_summary(),
            enabled=True,
            enforcement_mode="mock_claims",
            safety=safety,
        )

    policy = TenantPolicyResolver.from_file(_tenant_policy_path(policy_payload))
    request = _access_request(action=action, payload=payload)
    decision = policy.evaluate(claims_resolution.claims, request)
    return PolicyEnforcementResult(
        status="allowed" if decision.allowed else "denied",
        operation=operation,
        action=action,
        reason=decision.reason,
        decision=decision,
        claims_summary=claims_resolution.claims.public_summary(),
        enabled=True,
        enforcement_mode="mock_claims",
        safety=safety,
    )


def enforce_boundary_policy(operation: str, payload: Mapping[str, Any]) -> PolicyEnforcementResult:
    result = evaluate_boundary_policy(operation, payload)
    if not result.allowed:
        raise PolicyEnforcementDenied(result)
    return result


def _policy_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    raw = payload.get("bi_policy", {})
    return raw if isinstance(raw, Mapping) else {}


def _scope_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    raw = payload.get("bi_scope", {})
    return raw if isinstance(raw, Mapping) else {}


def _resolve_claims(policy_payload: Mapping[str, Any]):
    if "identity_key" not in policy_payload and os.environ.get("ANDY_BI_IDENTITY_KEY"):
        policy_payload = {**dict(policy_payload), "identity_key": os.environ.get("ANDY_BI_IDENTITY_KEY")}
    if "mock_claims_file" not in policy_payload and os.environ.get(MOCK_CLAIMS_FILE_ENV):
        policy_payload = {**dict(policy_payload), "mock_claims_file": os.environ.get(MOCK_CLAIMS_FILE_ENV)}
    return resolve_identity_for_policy(policy_payload)


def _tenant_policy_path(policy_payload: Mapping[str, Any]) -> Path:
    policy_file = policy_payload.get("tenant_policy_file") or os.environ.get(TENANT_POLICY_FILE_ENV)
    return Path(str(policy_file)).resolve() if policy_file else DEFAULT_TENANT_POLICY_FILE


def _access_request(*, action: str, payload: Mapping[str, Any]) -> AccessRequest:
    scope = _scope_payload(payload)
    return AccessRequest(
        action=action,
        tenant_id=_optional_text(scope.get("tenant_id")),
        state=_optional_text(scope.get("state")),
        source_root=_optional_text(scope.get("source_root")),
    )


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in TRUTHY


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
