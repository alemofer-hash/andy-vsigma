from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Protocol

from .identity import IdentityClaims, MockIdentityResolver


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROVIDER_CONFIG = ROOT / "config" / "andy_bi_identity_provider.example.json"
SUPPORTED_PROVIDER_TYPES = {"mock_claims", "oidc", "saml", "kerberos", "ldap"}
CORPORATE_PROVIDER_TYPES = {"oidc", "saml", "kerberos", "ldap"}


class IdentityProvider(Protocol):
    provider_type: str

    def resolve(self, identity_key: str | None = None) -> "IdentityProviderResult":
        ...


@dataclass(frozen=True)
class IdentityProviderResult:
    status: str
    provider_type: str
    claims: IdentityClaims | None = None
    reason: str = ""
    config_path: str = ""
    safety: dict[str, bool] = field(default_factory=dict)

    @property
    def resolved(self) -> bool:
        return self.status == "resolved" and self.claims is not None

    def public_summary(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "provider_type": self.provider_type,
            "reason": self.reason,
            "config_path": self.config_path,
            "claims": self.claims.public_summary() if self.claims else None,
            "safety": self.safety,
        }


class MockClaimsIdentityProvider:
    provider_type = "mock_claims"

    def __init__(self, *, config_path: str | Path | None = None, enabled: bool = True) -> None:
        self.config_path = Path(config_path) if config_path else None
        self.enabled = bool(enabled)

    def resolve(self, identity_key: str | None = None) -> IdentityProviderResult:
        result = MockIdentityResolver(enabled=self.enabled, config_path=self.config_path).resolve(identity_key)
        return IdentityProviderResult(
            status=result.status,
            provider_type=self.provider_type,
            claims=result.claims,
            reason=result.reason,
            config_path=result.config_path,
            safety={
                "connects_to_corporate_network": False,
                "stores_passwords": False,
                "uses_real_identity_provider": False,
                "provider_stub": False,
            },
        )


class CorporateIdentityAdapterStub:
    """Non-operational placeholder for future corporate identity adapters."""

    def __init__(self, provider_type: str, *, config_path: str | Path | None = None, enabled: bool = False) -> None:
        self.provider_type = str(provider_type or "").strip().lower()
        self.config_path = Path(config_path) if config_path else DEFAULT_PROVIDER_CONFIG
        self.enabled = bool(enabled)

    def resolve(self, identity_key: str | None = None) -> IdentityProviderResult:
        status = "blocked" if self.enabled else "disabled"
        reason = (
            f"{self.provider_type}_corporate_identity_provider_stub_not_implemented"
            if self.enabled
            else f"{self.provider_type}_corporate_identity_provider_disabled"
        )
        return IdentityProviderResult(
            status=status,
            provider_type=self.provider_type,
            reason=reason,
            config_path=str(self.config_path),
            safety={
                "connects_to_corporate_network": False,
                "stores_passwords": False,
                "uses_real_identity_provider": False,
                "provider_stub": True,
            },
        )


class UnsupportedIdentityProvider:
    def __init__(self, provider_type: str) -> None:
        self.provider_type = str(provider_type or "").strip().lower() or "unknown"

    def resolve(self, identity_key: str | None = None) -> IdentityProviderResult:
        return IdentityProviderResult(
            status="blocked",
            provider_type=self.provider_type,
            reason="unsupported_identity_provider",
            safety={
                "connects_to_corporate_network": False,
                "stores_passwords": False,
                "uses_real_identity_provider": False,
                "provider_stub": True,
            },
        )


def build_identity_provider(policy_payload: Mapping[str, Any]) -> IdentityProvider:
    provider_type = str(policy_payload.get("identity_provider", "mock_claims") or "mock_claims").strip().lower()
    if provider_type in {"mock", "mock_claims"}:
        claims_file = policy_payload.get("mock_claims_file")
        return MockClaimsIdentityProvider(config_path=str(claims_file) if claims_file else None, enabled=True)
    if provider_type in CORPORATE_PROVIDER_TYPES:
        return CorporateIdentityAdapterStub(
            provider_type,
            config_path=_provider_config_path(policy_payload),
            enabled=_as_bool(policy_payload.get("provider_enabled")),
        )
    return UnsupportedIdentityProvider(provider_type)


def resolve_identity_for_policy(policy_payload: Mapping[str, Any]) -> IdentityProviderResult:
    identity_key = str(policy_payload.get("identity_key", "") or "").strip() or None
    provider = build_identity_provider(policy_payload)
    return provider.resolve(identity_key)


def load_provider_template(path: str | Path = DEFAULT_PROVIDER_CONFIG) -> dict[str, Any]:
    provider_path = Path(path)
    if not provider_path.exists():
        return {}
    try:
        data = json.loads(provider_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _provider_config_path(policy_payload: Mapping[str, Any]) -> str | None:
    value = policy_payload.get("identity_provider_config") or policy_payload.get("provider_config")
    text = str(value or "").strip()
    return text or None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on", "sim"}
