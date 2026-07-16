from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MOCK_CLAIMS_FILE = ROOT / "config" / "andy_bi_mock_claims.example.json"

TRUTHY = {"1", "true", "yes", "y", "on"}


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value else ()
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item) for item in value if str(item))
    return (str(value),)


@dataclass(frozen=True)
class IdentityClaims:
    """Normalized identity claims used by future ANDY BI authorization.

    The contract deliberately stores identity attributes and scopes, not
    passwords, secrets, refresh tokens or corporate credentials.
    """

    subject: str
    display_name: str
    email_or_employee_id: str
    groups: tuple[str, ...] = field(default_factory=tuple)
    roles: tuple[str, ...] = field(default_factory=tuple)
    distributor_scope: tuple[str, ...] = field(default_factory=tuple)
    state_scope: tuple[str, ...] = field(default_factory=tuple)
    source_scope: tuple[str, ...] = field(default_factory=tuple)
    claims_source: str = "mock"
    auth_method: str = "mock"

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "IdentityClaims":
        return cls(
            subject=str(data.get("subject", "")).strip(),
            display_name=str(data.get("display_name", "")).strip(),
            email_or_employee_id=str(data.get("email_or_employee_id", "")).strip(),
            groups=_as_tuple(data.get("groups")),
            roles=_as_tuple(data.get("roles")),
            distributor_scope=_as_tuple(data.get("distributor_scope")),
            state_scope=_as_tuple(data.get("state_scope")),
            source_scope=_as_tuple(data.get("source_scope")),
            claims_source=str(data.get("claims_source", "mock")).strip() or "mock",
            auth_method=str(data.get("auth_method", "mock")).strip() or "mock",
        )

    def validate(self) -> list[str]:
        failures: list[str] = []
        if not self.subject:
            failures.append("subject_required")
        if not self.display_name:
            failures.append("display_name_required")
        if not self.email_or_employee_id:
            failures.append("email_or_employee_id_required")
        if not self.roles:
            failures.append("roles_required")
        if not self.distributor_scope:
            failures.append("distributor_scope_required")
        if not self.state_scope:
            failures.append("state_scope_required")
        return failures

    def public_summary(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "display_name": self.display_name,
            "groups_count": len(self.groups),
            "roles": list(self.roles),
            "distributor_scope": list(self.distributor_scope),
            "state_scope": list(self.state_scope),
            "source_scope_count": len(self.source_scope),
            "claims_source": self.claims_source,
            "auth_method": self.auth_method,
        }


@dataclass(frozen=True)
class MockIdentityResolution:
    status: str
    claims: IdentityClaims | None = None
    reason: str = ""
    config_path: str = ""
    safety: dict[str, bool] = field(default_factory=dict)

    @property
    def enabled(self) -> bool:
        return self.status == "resolved"

    def public_summary(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "config_path": self.config_path,
            "claims": self.claims.public_summary() if self.claims else None,
            "safety": self.safety,
        }


class MockIdentityResolver:
    """Local fictitious identity resolver for RBAC/ABAC tests.

    It is disabled unless explicitly enabled by constructor argument or by the
    `ANDY_BI_IDENTITY_MOCK_ENABLED=1` environment variable. It never performs
    network calls and never asks for or persists a password.
    """

    def __init__(self, *, enabled: bool | None = None, config_path: str | Path | None = None) -> None:
        self._enabled = enabled
        env_config = os.environ.get("ANDY_BI_MOCK_CLAIMS_FILE")
        self.config_path = Path(config_path or env_config or DEFAULT_MOCK_CLAIMS_FILE)

    def is_enabled(self) -> bool:
        if self._enabled is not None:
            return bool(self._enabled)
        return os.environ.get("ANDY_BI_IDENTITY_MOCK_ENABLED", "").strip().lower() in TRUTHY

    def resolve(self, identity_key: str | None = None) -> MockIdentityResolution:
        safety = {
            "network_calls": False,
            "password_storage": False,
            "requires_real_identity_provider": False,
        }
        if not self.is_enabled():
            return MockIdentityResolution(
                status="disabled",
                reason="mock_identity_disabled_by_default",
                config_path=str(self.config_path),
                safety=safety,
            )
        data = self._load_config()
        if data.get("mock_enabled") is not True:
            return MockIdentityResolution(
                status="blocked",
                reason="mock_config_must_set_mock_enabled_true",
                config_path=str(self.config_path),
                safety=safety,
            )
        identities = data.get("identities", [])
        if not isinstance(identities, list):
            return MockIdentityResolution(
                status="blocked",
                reason="identities_must_be_a_list",
                config_path=str(self.config_path),
                safety=safety,
            )
        selected = self._select_identity(identities, identity_key or data.get("default_identity"))
        if selected is None:
            return MockIdentityResolution(
                status="not_found",
                reason="mock_identity_not_found",
                config_path=str(self.config_path),
                safety=safety,
            )
        claims = IdentityClaims.from_mapping(selected)
        failures = claims.validate()
        if failures:
            return MockIdentityResolution(
                status="blocked",
                reason="invalid_claims:" + ",".join(failures),
                config_path=str(self.config_path),
                safety=safety,
            )
        return MockIdentityResolution(
            status="resolved",
            claims=claims,
            reason="mock_identity_resolved",
            config_path=str(self.config_path),
            safety=safety,
        )

    def available_identity_keys(self) -> tuple[str, ...]:
        data = self._load_config()
        identities = data.get("identities", [])
        if not isinstance(identities, list):
            return ()
        keys = [str(item.get("identity_key", "")) for item in identities if isinstance(item, dict)]
        return tuple(key for key in keys if key)

    @staticmethod
    def _select_identity(identities: list[Any], identity_key: Any) -> dict[str, Any] | None:
        dicts = [item for item in identities if isinstance(item, dict)]
        if not dicts:
            return None
        key = str(identity_key or "").strip()
        if key:
            for item in dicts:
                if str(item.get("identity_key", "")).strip() == key:
                    return item
            return None
        return dicts[0]

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {}
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}
